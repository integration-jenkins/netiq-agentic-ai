"""Offline model lifecycle, startup verification, and selection management."""

import logging
from typing import Any
from app.llms.model_registry import (
    APPROVED_MODEL_FAMILIES,
    APPROVED_MODELS,
    ModelCapability,
    ModelVerificationError,
    normalize_model_name,
)
from src.adapters.llm.provider import OllamaProvider, default_llm_provider
from src.settings.env import settings
from src.settings.loader import load_models_config

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages model selection, health checks, and startup validation for local Ollama models."""

    def __init__(self, provider: OllamaProvider | None = None) -> None:
        self.provider = provider or default_llm_provider
        self._verified_cache: dict[str, ModelCapability] = {}

    def get_configured_model(self, role: str | None = None) -> str:
        """Resolve model name based on role or system default config.
        
        Resolution Order:
        1. Role override in `configs/models.yaml` (if role provided).
        2. `default_model` in `configs/models.yaml`.
        3. `DEFAULT_LLM_MODEL` in environment / Settings.
        """
        raw_model = settings.default_llm_model
        try:
            cfg = load_models_config()
            if role and "roles" in cfg and role in cfg["roles"]:
                raw_model = cfg["roles"][role].get("model", cfg.get("default_model", settings.default_llm_model))
            else:
                raw_model = cfg.get("default_model", settings.default_llm_model)
        except Exception:
            raw_model = settings.default_llm_model

        normalized = normalize_model_name(raw_model)
        return normalized or raw_model

    async def verify_model_available(self, model_name: str) -> bool:
        """Verify whether a model is currently installed and ready in Ollama."""
        target = normalize_model_name(model_name) or model_name
        try:
            installed = await self.provider.list_installed_models()
            for m in installed:
                if m == target or m.startswith(f"{target}:"):
                    return True
            return False
        except Exception:
            return False

    async def inspect_and_verify_model(self, model_tag: str) -> ModelCapability:
        """Inspect actual model metadata from Ollama /api/show and verify against allowlist.
        
        Raises:
            ModelVerificationError: If model is missing, not installed, or has unapproved architecture.
        """
        target = normalize_model_name(model_tag) or model_tag
        if target in self._verified_cache:
            return self._verified_cache[target]

        try:
            info = await self.provider.inspect_model(target)
        except Exception as e:
            raise ModelVerificationError(
                f"Startup model verification failed for '{target}': {e}. "
                "Ensure model is installed offline in Ollama. Automatic downloading is prohibited."
            ) from e

        details = info.get("details", {})
        family = (details.get("family") or info.get("model_info", {}).get("general.architecture") or "").lower()
        param_size = details.get("parameter_size", "unknown")
        quant = details.get("quantization_level", "unknown")

        if family not in APPROVED_MODEL_FAMILIES:
            raise ModelVerificationError(
                f"Model '{target}' has unapproved architecture family '{family}'. "
                f"Approved families: {sorted(APPROVED_MODEL_FAMILIES)}"
            )

        cap = ModelCapability(
            name=target,
            display_name=APPROVED_MODELS.get(target, ModelCapability(
                name=target,
                display_name=target,
                family=family,
                parameter_size=param_size,
                quantization=quant,
                purpose="Configured local model"
            )).display_name,
            family=family,
            parameter_size=param_size,
            quantization=quant,
            context_length=32768,
            purpose=f"Verified runtime model ({family}, {param_size}, {quant})",
            verified=True,
            digest=info.get("digest"),
        )
        self._verified_cache[target] = cap
        return cap

    async def validate_startup_models(self, fail_closed: bool = True) -> dict[str, ModelCapability]:
        """Validate all configured default and role models on application startup.
        
        Guarantees:
        1. Fail-closed: Rejects missing or unapproved models.
        2. No internet egress: Does not call pull or external registries.
        """
        verified_results = {}
        try:
            cfg = load_models_config()
            models_to_check = {cfg.get("default_model", settings.default_llm_model)}
            for r_name, r_cfg in cfg.get("roles", {}).items():
                if "model" in r_cfg:
                    models_to_check.add(r_cfg["model"])
        except Exception as e:
            logger.warning("Could not read configs/models.yaml during validation: %s", e)
            models_to_check = {settings.default_llm_model}

        for model_tag in models_to_check:
            try:
                cap = await self.inspect_and_verify_model(model_tag)
                verified_results[model_tag] = cap
                logger.info("Verified local model '%s' (Family: %s, Size: %s)", model_tag, cap.family, cap.parameter_size)
            except ModelVerificationError as mve:
                if fail_closed:
                    raise
                else:
                    logger.error("Model verification failed for '%s': %s", model_tag, mve)

        return verified_results

    def get_model_capability(self, model_name: str) -> ModelCapability | None:
        """Lookup model capabilities from cache or static registry."""
        target = normalize_model_name(model_name) or model_name
        if target in self._verified_cache:
            return self._verified_cache[target]
        return APPROVED_MODELS.get(target)


default_model_manager = ModelManager()
