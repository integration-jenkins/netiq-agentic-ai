"""Metadata API routes exposing authorized circles, domains, report catalog, and testable agents."""

from fastapi import Header, HTTPException, Query

from app.llms.model_manager import default_model_manager
from src.security.authentication import AuthManager, AuthenticationError
from src.settings.loader import (
    ConfigurationError,
    load_catalog_config,
    load_models_config,
    load_report_definition,
)

# Standard circle catalog codes when user has wildcard '*' access
_STANDARD_CIRCLES = ["BR", "DL", "HR", "MH", "PB", "KA", "TN", "UPW", "UPE", "GJ", "RJ"]

_TESTABLE_AGENTS = [
    {
        "id": "intent_classifier",
        "name": "Intent Classifier",
        "role": "intent_classifier",
        "description": "Classifies user questions into REPORT, KNOWLEDGE, COMPARISON, SQL, or EXPORT.",
    },
    {
        "id": "report_selector",
        "name": "Report Selector",
        "role": "report_selector",
        "description": "Matches questions against verified NETIQ report catalog metadata (MATCH / AMBIGUOUS / NO_MATCH).",
    },
    {
        "id": "orchestrator_planner",
        "name": "Orchestrator / Planner",
        "role": "orchestrator_planner",
        "description": "Generates and validates structured Pydantic v2 ExecutionPlan steps.",
    },
    {
        "id": "knowledge_agent",
        "name": "Knowledge Agent",
        "role": "knowledge_agent",
        "description": "Provides retrieval-grounded telecom answers with SOP citations and threshold verification.",
    },
    {
        "id": "knowledge_retriever",
        "name": "Knowledge Retriever",
        "role": "knowledge_retriever",
        "description": "Retrieves matching local telecom SOP and glossary documents.",
    },
    {
        "id": "sql_agent",
        "name": "SQL Agent (Controlled)",
        "role": "sql_agent",
        "description": "Generates and validates Oracle 19c SQL proposals via SQLGlot without executing them.",
    },
]


async def list_circles(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> dict:
    """Retrieve telecom circles authorized for the calling user."""
    try:
        user = AuthManager.authenticate_incoming_request(authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    if user.is_admin or "*" in user.permitted_circles:
        circles = list(_STANDARD_CIRCLES)
    else:
        circles = sorted({c.strip().upper() for c in user.permitted_circles if c})

    return {"circles": circles, "is_wildcard": user.is_admin or "*" in user.permitted_circles}


async def list_domains(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> dict:
    """Retrieve supported telecom domains dynamically from report catalog."""
    try:
        AuthManager.authenticate_incoming_request(authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    try:
        catalog = load_catalog_config()
    except ConfigurationError as err:
        raise HTTPException(status_code=500, detail=str(err))

    domains = sorted({r.get("domain") for r in catalog.get("reports", []) if r.get("domain")})
    return {"domains": domains, "count": len(domains)}


async def list_reports(
    domain: str | None = Query(default=None, description="Optional domain filter"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> dict:
    """List permitted reports from configs/reports/catalog.yaml."""
    try:
        AuthManager.authenticate_incoming_request(authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    try:
        catalog = load_catalog_config()
    except ConfigurationError as err:
        raise HTTPException(status_code=500, detail=str(err))

    reports = catalog.get("reports", [])
    if domain:
        d_lower = domain.strip().lower()
        reports = [r for r in reports if r.get("domain", "").lower() == d_lower]

    return {
        "metadata_version": catalog.get("metadata_version"),
        "total_reports": len(reports),
        "reports": reports,
    }


async def get_report(
    report_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> dict:
    """Return one report's full definition from its domain YAML file."""
    try:
        AuthManager.authenticate_incoming_request(authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    try:
        return load_report_definition(report_id)
    except ConfigurationError as err:
        raise HTTPException(status_code=404, detail=str(err))


async def list_agents(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> dict:
    """Return available testable agents enriched with configured model names."""
    try:
        AuthManager.authenticate_incoming_request(authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    try:
        models_cfg = load_models_config()
        roles_cfg = models_cfg.get("roles", {})
        default_model = models_cfg.get("default_model", "qwen3:4b-instruct-2507")
    except Exception:
        roles_cfg = {}
        default_model = "qwen3:4b-instruct-2507"

    enriched = []
    for agent in _TESTABLE_AGENTS:
        role_info = roles_cfg.get(agent["role"], {})
        enriched.append({
            **agent,
            "configured_model": role_info.get("model", default_model),
            "display_name": role_info.get("display_name", role_info.get("model", default_model)),
        })

    return {"agents": enriched, "count": len(enriched)}


async def list_models(
    refresh: bool = Query(default=False, description="Force live Ollama re-inspection"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> dict:
    """Return verified physical model inventory per agent role. Restricted to developers/admins."""
    try:
        user = AuthManager.authenticate_incoming_request(authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    if not (user.is_admin or user.has_role("developer")):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Developer or administrator privileges required to inspect detailed model inventory.",
        )

    if refresh or not default_model_manager.get_identity_records():
        await default_model_manager.validate_startup_models(fail_closed=False)

    records = default_model_manager.get_identity_records()
    models_out = [rec.model_dump() for rec in records.values()]
    return {
        "models": models_out,
        "count": len(models_out),
        "all_required_verified": all(
            rec.available for rec in records.values() if rec.required
        ),
    }
