"""Health-check and system diagnostics API routes."""

from datetime import datetime, timezone
from fastapi import Header, Query

from app.llms.model_manager import default_model_manager
from src.security.authentication import AuthManager
from src.settings.env import PROJECT_ROOT, settings
from src.settings.loader import load_catalog_config, load_models_config


async def health(
    details: bool = Query(default=False, description="Include detailed subsystem diagnostics"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> dict:
    """Liveness check and optional subsystem diagnostics for the System Health page."""
    base = {
        "status": "ok",
        "mode": settings.netiq_api_mode.value,
        "environment": settings.app_env.value,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if not details:
        return base

    # Basic user check; detailed internal diagnostics shown when admin or in non-prod dev
    is_admin = False
    try:
        user = AuthManager.authenticate_incoming_request(
            authorization=authorization,
            api_key=x_netiq_api_key,
            enforce=False,
        )
        is_admin = user.is_admin
    except Exception:
        pass

    # 1. Check Ollama connectivity & installed models
    ollama_status = "UNAVAILABLE"
    installed_models: list[str] = []
    try:
        installed_models = await default_model_manager.provider.list_installed_models()
        ollama_status = "CONNECTED"
    except Exception:
        ollama_status = "UNAVAILABLE"

    # 2. Check configured models & identity verification
    try:
        models_cfg = load_models_config()
        configured_model = models_cfg.get("default_model", settings.default_llm_model)
    except Exception:
        configured_model = settings.default_llm_model

    model_available = any(
        m == configured_model or m.startswith(f"{configured_model}:")
        for m in installed_models
    )

    identity_records = default_model_manager.get_identity_records()
    if not identity_records and ollama_status == "CONNECTED":
        try:
            identity_records = await default_model_manager.validate_startup_models(fail_closed=False)
        except Exception:
            identity_records = {}

    mismatches = {
        role: {"status": rec.status.value, "reason": rec.mismatch_reason}
        for role, rec in identity_records.items()
        if rec.status.value != "VERIFIED"
    }

    # 3. Check Report Catalog readiness
    report_count = 0
    catalog_ready = False
    try:
        cat = load_catalog_config()
        report_count = len(cat.get("reports", []))
        catalog_ready = report_count > 0
    except Exception:
        pass

    # 4. Check Knowledge Base readiness
    kb_dir = PROJECT_ROOT / "knowledge_base"
    kb_files = list(kb_dir.rglob("*.md")) if kb_dir.is_dir() else []

    payload = {
        **base,
        "fastapi_available": True,
        "ollama_status": ollama_status,
        "configured_model": configured_model,
        "configured_model_available": model_available,
        "model_identity_verified": len(mismatches) == 0 and bool(identity_records),
        "model_mismatches": mismatches,
        "report_catalog_ready": catalog_ready,
        "report_count": report_count,
        "knowledge_index_ready": len(kb_files) > 0,
        "knowledge_documents": len(kb_files),
        "java_api_mode": settings.netiq_api_mode.value,
        "java_api_status": "MOCK_FIXTURES" if settings.netiq_api_mode.value == "MOCK" else "LIVE_CONFIGURED",
        "live_sql_enabled": settings.live_sql_execution_enabled,
    }
    if is_admin:
        payload["installed_models"] = installed_models
        payload["ollama_base_url"] = settings.ollama_base_url
    return payload
