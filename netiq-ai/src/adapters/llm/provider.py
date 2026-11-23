"""LLM provider adapter for local Ollama inference in NETIQ Agentic AI.

Architecture Role:
------------------
This module acts as the infrastructure adapter for local offline LLM inference.
It communicates with the Ollama REST API (`/api/generate`, `/api/chat`, `/api/tags`, `/api/show`),
gathers granular performance metrics (speed, latency, token throughput), and translates
low-level HTTP/JSON payloads into typed completion results.

Key Guarantees:
---------------
1. Configurable Model Name: The model name is a configuration setting and can be overridden.
2. Speed and Quality Metrics: Captures wall duration, eval tokens/sec, and prompt eval duration.
3. Concurrency Limits: Enforces bounded async concurrency via semaphore to protect GPU VRAM.
4. Fail-Closed Error Handling: Cleanly maps connection, model-missing, and timeout errors without leaking secrets.
"""

import asyncio
import time
from typing import Any
import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.settings.env import settings
from src.settings.loader import load_models_config


class LLMMetrics(BaseModel):
    """Performance and speed metrics returned by Ollama runtime."""
    model_config = ConfigDict(frozen=True)

    total_duration_seconds: float = Field(..., description="Total wall-clock duration in seconds")
    eval_count_tokens: int = Field(default=0, description="Tokens generated in output response")
    eval_tokens_per_second: float = Field(default=0.0, description="Generation speed (eval tokens / sec)")
    prompt_eval_count_tokens: int = Field(default=0, description="Tokens processed in input prompt")
    prompt_eval_duration_seconds: float = Field(default=0.0, description="Prompt ingestion duration in seconds")


class LLMResult(BaseModel):
    """Normalized output from local LLM completion."""
    model_config = ConfigDict(frozen=True)

    model: str = Field(..., description="Actual model name used for generation")
    response_text: str = Field(..., description="Generated completion text")
    metrics: LLMMetrics = Field(..., description="Speed and latency performance metrics")
    done: bool = Field(default=True, description="Whether generation completed successfully")


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class OllamaConnectionError(LLMProviderError):
    """Raised when Ollama daemon cannot be reached."""
    pass


class OllamaModelNotFoundError(LLMProviderError):
    """Raised when requested model is not downloaded or available on Ollama."""
    pass


class OllamaTimeoutError(LLMProviderError):
    """Raised when an inference call times out."""
    pass


class OllamaConcurrencyLimitError(LLMProviderError):
    """Raised when concurrent inference capacity is saturated."""
    pass


class OllamaProvider:
    """Async client communicating with local Ollama daemon with concurrency and latency tracking."""

    def __init__(
        self,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout_seconds: float | None = None,
        max_concurrency: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Initialize the Ollama provider adapter."""
        try:
            cfg = load_models_config()
            cfg_model = cfg.get("default_model")
            cfg_url = cfg.get("ollama_base_url")
            cfg_timeout = cfg.get("timeout_seconds")
        except Exception:
            cfg_model, cfg_url, cfg_timeout = None, None, None

        self.base_url = (base_url or cfg_url or settings.ollama_base_url).rstrip("/")
        self.default_model = default_model or cfg_model or settings.default_llm_model
        self.timeout = float(timeout_seconds or cfg_timeout or settings.llm_timeout_seconds)
        self.concurrency_limit = max_concurrency or settings.llm_max_concurrency
        self._semaphore = asyncio.Semaphore(self.concurrency_limit)

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
            transport=transport,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

    async def close(self) -> None:
        """Close HTTP client session."""
        await self._client.aclose()

    async def __aenter__(self) -> "OllamaProvider":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def list_installed_models(self) -> list[str]:
        """Fetch list of model tags currently installed in local Ollama daemon."""
        try:
            resp = await self._client.get("/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                return models
            return []
        except httpx.RequestError as e:
            raise OllamaConnectionError(f"Failed to connect to Ollama at {self.base_url}: {e}") from e

    async def inspect_model(self, model_name: str) -> dict[str, Any]:
        """Query Ollama /api/show to inspect real physical model details."""
        try:
            resp = await self._client.post("/api/show", json={"name": model_name})
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                raise OllamaModelNotFoundError(f"Model '{model_name}' not found in Ollama repository.")
            else:
                raise LLMProviderError(f"Ollama returned HTTP {resp.status_code} during model inspection.")
        except httpx.RequestError as e:
            raise OllamaConnectionError(f"Failed to inspect model '{model_name}' at {self.base_url}: {e}") from e

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        role: str | None = None,
        format: str | None = None,
    ) -> LLMResult:
        """Execute text completion and return normalized result with speed metrics."""
        selected_model = model or self.default_model
        selected_temp = temperature if temperature is not None else 0.0
        selected_num_predict = max_tokens

        # Check role configurations from models.yaml
        if role:
            try:
                cfg = load_models_config()
                role_cfg = cfg.get("roles", {}).get(role, {})
                if not model and "model" in role_cfg:
                    selected_model = role_cfg["model"]
                if temperature is None and "temperature" in role_cfg:
                    selected_temp = float(role_cfg["temperature"])
                if max_tokens is None and "max_tokens" in role_cfg:
                    selected_num_predict = int(role_cfg["max_tokens"])
            except Exception:
                pass

        # Normalize model name if alias or display name was provided
        try:
            from app.llms.model_registry import normalize_model_name
            normalized = normalize_model_name(selected_model)
            if normalized:
                selected_model = normalized
        except Exception:
            pass

        payload: dict[str, Any] = {
            "model": selected_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": selected_temp,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt
        if selected_num_predict:
            payload["options"]["num_predict"] = selected_num_predict
        if format:
            payload["format"] = format

        # Apply concurrency guard
        async with self._semaphore:
            wall_start = time.perf_counter()
            try:
                resp = await self._client.post("/api/generate", json=payload)
            except httpx.TimeoutException as te:
                raise OllamaTimeoutError(f"Inference request timed out after {self.timeout}s: {te}") from te
            except httpx.RequestError as re:
                raise OllamaConnectionError(
                    f"Cannot connect to local Ollama instance at {self.base_url}. Ensure 'ollama serve' is running."
                ) from re

            wall_duration = time.perf_counter() - wall_start

            if resp.status_code == 404:
                raise OllamaModelNotFoundError(
                    f"Model '{selected_model}' not found on Ollama. Please install it offline via Ollama."
                )
            elif resp.status_code != 200:
                raise LLMProviderError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            eval_count = data.get("eval_count", 0)
            eval_duration_sec = data.get("eval_duration", 0) / 1e9
            tok_per_sec = (eval_count / eval_duration_sec) if eval_duration_sec > 0 else 0.0
            prompt_eval_count = data.get("prompt_eval_count", 0)
            prompt_eval_duration_sec = data.get("prompt_eval_duration", 0) / 1e9

            metrics = LLMMetrics(
                total_duration_seconds=round(wall_duration, 4),
                eval_count_tokens=eval_count,
                eval_tokens_per_second=round(tok_per_sec, 2),
                prompt_eval_count_tokens=prompt_eval_count,
                prompt_eval_duration_seconds=round(prompt_eval_duration_sec, 4),
            )

            return LLMResult(
                model=selected_model,
                response_text=data.get("response", "").strip(),
                metrics=metrics,
                done=data.get("done", True),
            )


# Default singleton provider instance
default_llm_provider = OllamaProvider()
