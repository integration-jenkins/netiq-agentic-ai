"""Inference API route exposing the local Ollama LLM with speed, quality, and enterprise security."""

import logging
import uuid
from typing import Any
from fastapi import Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.llms.llm_client import default_llm_client
from app.llms.model_registry import APPROVED_MODELS, normalize_model_name
from src.adapters.llm.provider import (
    LLMMetrics,
    OllamaConcurrencyLimitError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)
from src.security.authentication import AuthManager, AuthenticationError
from src.settings.env import settings

logger = logging.getLogger(__name__)

# Permitted agent roles for role-based parameter and policy resolution
ALLOWED_ROLES = {
    "intent_classifier",
    "report_selector",
    "orchestrator_planner",
    "knowledge_agent",
    "sql_agent",
    "general",
}


class InferenceRequest(BaseModel):
    """Payload for executing LLM inference with strict input bounds."""
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_prompt_chars,
        description="Prompt text to send to LLM",
        examples=["What is an eNodeB in telecom?"]
    )
    model: str | None = Field(
        default=None,
        description="Optional model override. Must exist in approved model allowlist."
    )
    system_prompt: str | None = Field(
        default=None,
        max_length=4000,
        description="Optional system instruction. Permitted ONLY for admin or trusted internal callers."
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (0.0 for deterministic outputs)"
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=settings.max_generation_tokens,
        description="Maximum generated token limit"
    )
    role: str | None = Field(
        default=None,
        description="Optional role mapping ('intent_classifier', 'report_selector', 'sql_agent', etc.)"
    )


class InferenceResponse(BaseModel):
    """Inference completion result with speed, audit, and quality performance metrics."""
    status: str = Field(default="SUCCESS", description="Execution status")
    correlation_id: str = Field(..., description="Unique request tracing correlation ID")
    model: str = Field(..., description="Model name utilized for generation")
    response: str = Field(..., description="Generated text completion")
    metrics: LLMMetrics = Field(..., description="Detailed speed, throughput, and latency metrics")


async def inference_endpoint(
    request: InferenceRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
) -> InferenceResponse:
    """Execute secured local LLM inference and return result with speed metrics.
    
    Security Controls Enforced:
    1. Authentication: Requires valid Bearer token or API key if auth enforcement is active.
    2. System Prompt Gate: Normal users are strictly forbidden from overriding system prompts.
    3. Model Allowlist: Restricts model selection to approved registry items.
    4. Role Boundary: Validates role against approved role allowlist.
    5. Concurrency & Timeout: Managed via async semaphore and client timeout.
    6. Audit Logging: Structured audit trail recorded with correlation ID.
    """
    correlation_id = x_correlation_id or str(uuid.uuid4())

    # 1. Enforce Authentication
    try:
        user_ctx = AuthManager.authenticate_incoming_request(
            authorization=authorization,
            api_key=x_netiq_api_key,
        )
    except AuthenticationError as auth_err:
        raise HTTPException(status_code=401, detail=str(auth_err))

    # 2. Prevent Normal Users from Injecting Arbitrary System Prompts
    if request.system_prompt is not None and not user_ctx.is_admin:
        logger.warning(
            "User '%s' attempted unauthorized system_prompt override. CID: %s",
            user_ctx.username,
            correlation_id,
        )
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Custom system prompts are restricted to administrative or internal agents."
        )

    # 3. Restrict Model Selection to Approved Models
    if request.model:
        normalized_target = normalize_model_name(request.model)
        if normalized_target not in APPROVED_MODELS:
            logger.warning("Rejected unapproved model '%s'. CID: %s", request.model, correlation_id)
            raise HTTPException(
                status_code=403,
                detail=f"Model '{request.model}' is not in the approved model allowlist."
            )

    # 4. Validate Role
    if request.role and request.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent role '{request.role}'. Permitted roles: {sorted(ALLOWED_ROLES)}"
        )

    # 5. Execute Inference
    try:
        result = await default_llm_client.generate_completion(
            prompt=request.prompt,
            model=request.model,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            role=request.role,
        )

        logger.info(
            "Inference completed. CID=%s User=%s Role=%s Model=%s Tokens=%d Latency=%.3fs",
            correlation_id,
            user_ctx.username,
            request.role or "default",
            result.model,
            result.metrics.eval_count_tokens,
            result.metrics.total_duration_seconds,
        )

        return InferenceResponse(
            status="SUCCESS",
            correlation_id=correlation_id,
            model=result.model,
            response=result.response_text,
            metrics=result.metrics,
        )

    except OllamaModelNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except OllamaConcurrencyLimitError as cle:
        raise HTTPException(status_code=429, detail="Inference capacity saturated. Please retry shortly.")
    except OllamaConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail="Local LLM service unavailable. Ensure local Ollama daemon is active ('ollama serve')."
        )
    except OllamaTimeoutError as e:
        raise HTTPException(status_code=504, detail="LLM inference timed out.")
    except Exception as e:
        logger.error("Unhandled inference exception CID=%s: %s", correlation_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal inference execution failure.")
