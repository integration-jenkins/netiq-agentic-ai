"""Offline model lifecycle, strict identity verification, and selection management."""

import logging
from datetime import datetime, timezone
from typing import Any

from app.llms.model_registry import (
    APPROVED_MODELS,
    ModelCapability,
    ModelIdentityExpectation,
    ModelVerificationError,
    ModelVerificationStatus,
    VerifiedModelRecord,
    normalize_model_name,
    parse_parameter_billions,
)
from src.adapters.llm.provider import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaProvider,
    default_llm_provider,
)
from src.settings.env import settings
from src.settings.loader import load_models_config

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages model selection, physical identity checks, and fail-closed validation."""

    def __init__(self, provider: OllamaProvider | None = None) -> None:
        self.provider = provider or default_llm_provider
        self._verified_cache: dict[str, ModelCapability] = {}
        self._identity_records: dict[str, VerifiedModelRecord] = {}
        self._disabled_roles: set[str] = set()

    def clear_cache(self) -> None:
        self._verified_cache.clear()
        self._identity_records.clear()
        self._disabled_roles.clear()

    def get_configured_model(self, role: str | None = None) -> str:
        """Resolve model tag based on role or system default config."""
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

    def is_role_available(self, role: str) -> bool:
        """Check if a role passed identity verification and is enabled."""
        if role in self._disabled_roles:
            return False
        rec = self._identity_records.get(role)
        if rec is not None:
            return rec.available
        return True

    def get_identity_records(self) -> dict[str, VerifiedModelRecord]:
        """Return cached physical verification records keyed by role."""
        return dict(self._identity_records)

    async def verify_model_available(self, model_name: str) -> bool:
        """Verify whether a model tag is currently installed in Ollama."""
        target = normalize_model_name(model_name) or model_name
        try:
            installed = await self.provider.list_installed_models()
            return any(m == target or m.startswith(f"{target}:") for m in installed)
        except Exception:
            return False

    async def verify_model_identity(
        self,
        role: str,
        expectation: ModelIdentityExpectation,
        installed_map: dict[str, dict[str, Any]] | None = None,
        embedding_dimensions: int | None = None,
    ) -> VerifiedModelRecord:
        """Verify a configured model against actual Ollama runtime metadata (/api/tags + /api/show)."""
        target = normalize_model_name(expectation.tag) or expectation.tag
        now_iso = datetime.now(timezone.utc).isoformat()
        expected_param_str = (
            f"{expectation.expected_parameter_billions}B"
            if expectation.expected_parameter_billions is not None
            else None
        )

        # 1. Fetch installed tags/digests if not pre-loaded
        if installed_map is None:
            try:
                raw_tags = await self.provider.list_installed_models_detailed()
                installed_map = {m["name"]: m for m in raw_tags if m.get("name")}
            except OllamaConnectionError as err:
                rec = VerifiedModelRecord(
                    role=role,
                    configured_model_tag=target,
                    expected_architecture=expectation.expected_family,
                    expected_parameter_count=expected_param_str,
                    status=ModelVerificationStatus.VERIFICATION_UNAVAILABLE,
                    available=False,
                    required=expectation.required,
                    last_verified_at=now_iso,
                    mismatch_reason=f"Ollama daemon unreachable: {err}",
                )
                self._identity_records[role] = rec
                return rec

        # Match exact tag or :latest
        tag_entry = installed_map.get(target) or installed_map.get(f"{target}:latest")
        if tag_entry is None:
            rec = VerifiedModelRecord(
                role=role,
                configured_model_tag=target,
                expected_architecture=expectation.expected_family,
                expected_parameter_count=expected_param_str,
                status=ModelVerificationStatus.MODEL_NOT_FOUND,
                available=False,
                required=expectation.required,
                last_verified_at=now_iso,
                mismatch_reason=f"Model '{target}' is not installed locally in Ollama.",
            )
            self._identity_records[role] = rec
            return rec

        actual_tag = tag_entry.get("name", target)
        digest = tag_entry.get("digest")
        size_bytes = tag_entry.get("size")

        # 2. Inspect physical model details via /api/show
        try:
            show_info = await self.provider.inspect_model(actual_tag)
        except OllamaModelNotFoundError:
            rec = VerifiedModelRecord(
                role=role,
                configured_model_tag=target,
                actual_model_tag=actual_tag,
                expected_architecture=expectation.expected_family,
                expected_parameter_count=expected_param_str,
                digest=digest,
                size_bytes=size_bytes,
                status=ModelVerificationStatus.MODEL_NOT_FOUND,
                available=False,
                required=expectation.required,
                last_verified_at=now_iso,
                mismatch_reason=f"Model '{actual_tag}' returned 404 on /api/show.",
            )
            self._identity_records[role] = rec
            return rec
        except OllamaConnectionError as err:
            rec = VerifiedModelRecord(
                role=role,
                configured_model_tag=target,
                actual_model_tag=actual_tag,
                expected_architecture=expectation.expected_family,
                expected_parameter_count=expected_param_str,
                status=ModelVerificationStatus.VERIFICATION_UNAVAILABLE,
                available=False,
                required=expectation.required,
                last_verified_at=now_iso,
                mismatch_reason=f"Ollama connection lost during /api/show: {err}",
            )
            self._identity_records[role] = rec
            return rec

        details = show_info.get("details", {})
        model_info = show_info.get("model_info", {})
        detected_family = (
            details.get("family") or model_info.get("general.architecture") or ""
        ).strip().lower()
        detected_param_str = details.get("parameter_size")
        detected_quant = details.get("quantization_level")
        capabilities = [str(c).lower() for c in show_info.get("capabilities", [])]

        def _fail(status: ModelVerificationStatus, reason: str) -> VerifiedModelRecord:
            failed = VerifiedModelRecord(
                role=role,
                configured_model_tag=target,
                actual_model_tag=actual_tag,
                expected_architecture=expectation.expected_family,
                detected_architecture=detected_family or None,
                expected_parameter_count=expected_param_str,
                detected_parameter_count=detected_param_str,
                quantization=detected_quant,
                digest=digest,
                size_bytes=size_bytes,
                capabilities=capabilities,
                embedding_dimensions=embedding_dimensions,
                status=status,
                available=False,
                required=expectation.required,
                last_verified_at=now_iso,
                mismatch_reason=reason,
            )
            self._identity_records[role] = failed
            self._disabled_roles.add(role)
            logger.error("Model identity verification FAILED for role '%s' (%s): %s", role, status.value, reason)
            return failed

        # 3. Check Digest Pin if configured
        if expectation.expected_digest and digest and not digest.startswith(expectation.expected_digest):
            return _fail(
                ModelVerificationStatus.IDENTITY_MISMATCH,
                f"Digest mismatch: expected prefix '{expectation.expected_digest}', got '{digest[:16]}'.",
            )

        # 4. Check Architecture / Family
        if expectation.expected_family:
            exp_fam = expectation.expected_family.strip().lower()
            if not detected_family or (detected_family != exp_fam and not detected_family.startswith(exp_fam)):
                return _fail(
                    ModelVerificationStatus.IDENTITY_MISMATCH,
                    f"Architecture mismatch for '{target}': expected '{exp_fam}', detected '{detected_family or 'unknown'}'.",
                )

        # 5. Check Parameter Count within tolerance
        if expectation.expected_parameter_billions is not None:
            detected_b = parse_parameter_billions(detected_param_str)
            if detected_b is None:
                return _fail(
                    ModelVerificationStatus.IDENTITY_MISMATCH,
                    f"Could not parse detected parameter count '{detected_param_str}'.",
                )
            diff = abs(detected_b - expectation.expected_parameter_billions)
            if diff > expectation.parameter_tolerance_billions:
                return _fail(
                    ModelVerificationStatus.IDENTITY_MISMATCH,
                    f"Parameter count mismatch for '{target}': expected ~{expectation.expected_parameter_billions}B, "
                    f"detected {detected_param_str} ({detected_b:.3f}B).",
                )

        # 6. Check Quantization if configured
        if expectation.expected_quantization and detected_quant:
            if detected_quant.strip().upper() != expectation.expected_quantization.strip().upper():
                return _fail(
                    ModelVerificationStatus.IDENTITY_MISMATCH,
                    f"Quantization mismatch for '{target}': expected '{expectation.expected_quantization}', detected '{detected_quant}'.",
                )

        # 7. Check Capability (e.g. 'embedding' or 'completion') when reported by Ollama
        if expectation.expected_capability and capabilities:
            exp_cap = expectation.expected_capability.strip().lower()
            if exp_cap not in capabilities:
                return _fail(
                    ModelVerificationStatus.CAPABILITY_MISMATCH,
                    f"Capability mismatch for '{target}': expected '{exp_cap}', detected {capabilities}.",
                )

        # Passed all identity checks
        verified_rec = VerifiedModelRecord(
            role=role,
            configured_model_tag=target,
            actual_model_tag=actual_tag,
            expected_architecture=expectation.expected_family,
            detected_architecture=detected_family or None,
            expected_parameter_count=expected_param_str,
            detected_parameter_count=detected_param_str,
            quantization=detected_quant,
            digest=digest,
            size_bytes=size_bytes,
            capabilities=capabilities,
            embedding_dimensions=embedding_dimensions,
            status=ModelVerificationStatus.VERIFIED,
            available=True,
            required=expectation.required,
            last_verified_at=now_iso,
            mismatch_reason=None,
        )
        self._identity_records[role] = verified_rec
        self._disabled_roles.discard(role)

        self._verified_cache[target] = ModelCapability(
            name=target,
            display_name=APPROVED_MODELS.get(target, ModelCapability(
                name=target, display_name=target, family=detected_family or "unknown",
                parameter_size=detected_param_str or "unknown",
            )).display_name,
            family=detected_family or "unknown",
            parameter_size=detected_param_str or "unknown",
            quantization=detected_quant or "unknown",
            verified=True,
            digest=digest,
        )
        return verified_rec

    async def validate_startup_models(self, fail_closed: bool | None = None) -> dict[str, VerifiedModelRecord]:
        """Validate all configured role models against registry expectations on startup."""
        cfg = load_models_config()
        val_cfg = cfg.get("identity_validation", {})
        if not val_cfg.get("enabled", True):
            return {}

        should_fail_closed = fail_closed if fail_closed is not None else bool(val_cfg.get("fail_closed", True))
        registry_cfg = cfg.get("registry", {})
        roles_cfg = cfg.get("roles", {})

        # Pre-load installed tags once
        installed_map: dict[str, dict[str, Any]] | None = None
        try:
            raw_tags = await self.provider.list_installed_models_detailed()
            installed_map = {m["name"]: m for m in raw_tags if m.get("name")}
        except OllamaConnectionError:
            installed_map = None

        results: dict[str, VerifiedModelRecord] = {}
        for role_name, role_def in roles_cfg.items():
            reg_key = role_def.get("registry_key")
            reg_def = registry_cfg.get(reg_key, {}) if reg_key else {}
            tag = role_def.get("model") or reg_def.get("tag") or cfg.get("default_model", settings.default_llm_model)

            expectation = ModelIdentityExpectation(
                tag=tag,
                expected_family=reg_def.get("expected_family"),
                expected_parameter_billions=reg_def.get("expected_parameter_billions"),
                parameter_tolerance_billions=float(reg_def.get("parameter_tolerance_billions", 0.6)),
                expected_quantization=reg_def.get("expected_quantization"),
                expected_capability=reg_def.get("expected_capability"),
                expected_digest=reg_def.get("expected_digest"),
                required=bool(reg_def.get("required", True)),
            )

            rec = await self.verify_model_identity(
                role=role_name,
                expectation=expectation,
                installed_map=installed_map,
            )
            results[role_name] = rec

            if rec.status != ModelVerificationStatus.VERIFIED:
                if rec.required and should_fail_closed:
                    raise ModelVerificationError(
                        f"Mandatory model verification failed for role '{role_name}': {rec.mismatch_reason}",
                        status=rec.status,
                    )
                elif not rec.required:
                    logger.warning("Optional role '%s' disabled due to model verification failure: %s", role_name, rec.mismatch_reason)

        return results

    def get_model_capability(self, model_name: str) -> ModelCapability | None:
        """Lookup model capabilities from verified cache or static registry."""
        target = normalize_model_name(model_name) or model_name
        if target in self._verified_cache:
            return self._verified_cache[target]
        return APPROVED_MODELS.get(target)


default_model_manager = ModelManager()
