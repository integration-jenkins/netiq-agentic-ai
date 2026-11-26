"""Developer and administrator agent-testing API route (POST /v1/agents/test)."""

import time
from typing import Any
from fastapi import Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.llms.knowledge_agent import default_knowledge_agent
from app.llms.llm_client import default_llm_client
from app.llms.model_manager import default_model_manager
from app.llms.report_selector import default_report_selector
from app.orchestrator.chat_service import _load_knowledge_docs
from app.orchestrator.planner import default_orchestration_planner
from src.security.authentication import AuthManager, AuthenticationError
from src.security.sql_guard import OracleSQLGuard, SQLSecurityError


class AgentTestRequest(BaseModel):
    """Request payload for testing an individual NETIQ agent."""
    model_config = ConfigDict(extra="forbid")

    agent: str = Field(..., description="Agent ID ('intent_classifier', 'report_selector', 'orchestrator_planner', 'knowledge_agent', 'knowledge_retriever', 'sql_agent')")
    question: str = Field(..., min_length=1, max_length=4000, description="Input test question")
    circle: str | None = Field(default=None, description="Optional circle context")


class AgentTestResponse(BaseModel):
    """Standardized diagnostic response for developer agent testing."""
    status: str
    agent: str
    configured_model: str
    verified_model: dict[str, Any] | None = None
    output: Any = None
    structured_json: dict[str, Any] | list[Any] | None = None
    validation_status: str = "VALID"
    token_usage: dict[str, int] = Field(default_factory=dict)
    inference_latency_ms: int = 0
    total_latency_ms: int = 0
    error: str | None = None


async def test_agent(
    body: AgentTestRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> AgentTestResponse:
    """Execute and inspect an individual agent. Restricted to developers/administrators."""
    try:
        user = AuthManager.authenticate_incoming_request(authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    if not (user.is_admin or user.has_role("developer")):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Developer or administrator privileges required for agent testing.",
        )

    t0 = time.perf_counter()
    configured_model = default_model_manager.get_configured_model(role=body.agent)
    cap = default_model_manager.get_model_capability(configured_model)
    verified_meta = cap.model_dump() if cap else None

    try:
        if body.agent == "intent_classifier":
            res = await default_llm_client.classify_intent(body.question)
            return AgentTestResponse(
                status="SUCCESS",
                agent=body.agent,
                configured_model=configured_model,
                verified_model=verified_meta,
                output=res.response_text,
                structured_json={"intent": res.response_text},
                token_usage={
                    "prompt_tokens": res.metrics.prompt_eval_count_tokens,
                    "completion_tokens": res.metrics.eval_count_tokens,
                },
                inference_latency_ms=int(res.metrics.total_duration_seconds * 1000),
                total_latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        if body.agent == "report_selector":
            sel = default_report_selector.select_report(body.question)
            return AgentTestResponse(
                status="SUCCESS",
                agent=body.agent,
                configured_model=configured_model,
                verified_model=verified_meta,
                output=sel.explanation,
                structured_json=sel.model_dump(),
                validation_status=sel.status,
                total_latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        if body.agent == "orchestrator_planner":
            plan = await default_orchestration_planner.create_plan(body.question, user=user)
            return AgentTestResponse(
                status="SUCCESS",
                agent=body.agent,
                configured_model=configured_model,
                verified_model=verified_meta,
                output=plan.explanation,
                structured_json=plan.model_dump(),
                validation_status="VALIDATED" if plan.validated else "UNVALIDATED",
                total_latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        if body.agent == "knowledge_retriever":
            docs = _load_knowledge_docs()
            q_words = set(body.question.lower().split())
            matched = [
                d.model_dump()
                for d in docs
                if q_words.intersection(set(f"{d.doc_id} {d.title} {d.content}".lower().split()))
            ][:5]
            return AgentTestResponse(
                status="SUCCESS",
                agent=body.agent,
                configured_model=configured_model,
                verified_model=verified_meta,
                output=f"Retrieved {len(matched)} local knowledge documents.",
                structured_json=matched,
                total_latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        if body.agent == "knowledge_agent":
            docs = _load_knowledge_docs()[:2]
            ans = await default_knowledge_agent.answer_question(body.question, documents=docs)
            return AgentTestResponse(
                status="SUCCESS",
                agent=body.agent,
                configured_model=configured_model,
                verified_model=verified_meta,
                output=ans.answer,
                structured_json=ans.model_dump(),
                validation_status=ans.status,
                total_latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        if body.agent == "sql_agent":
            schema_hint = "TABLE ran_cells (cell_id, cell_name, circle, operational_status, last_down_timestamp)"
            res = await default_llm_client.generate_sql(body.question, schema_info=schema_hint)
            sql_proposal = res.response_text
            val_status = "VALIDATED_READ_ONLY"
            err_msg = None
            try:
                OracleSQLGuard.validate_query(sql_proposal, user=user, max_rows=100)
            except SQLSecurityError as s_err:
                val_status = "REJECTED_BY_SQL_GUARD"
                err_msg = str(s_err)

            return AgentTestResponse(
                status="SUCCESS",
                agent=body.agent,
                configured_model=configured_model,
                verified_model=verified_meta,
                output=sql_proposal,
                structured_json={"sql": sql_proposal, "live_execution": False},
                validation_status=val_status,
                token_usage={
                    "prompt_tokens": res.metrics.prompt_eval_count_tokens,
                    "completion_tokens": res.metrics.eval_count_tokens,
                },
                inference_latency_ms=int(res.metrics.total_duration_seconds * 1000),
                total_latency_ms=int((time.perf_counter() - t0) * 1000),
                error=err_msg,
            )

        raise HTTPException(status_code=400, detail=f"Unknown agent '{body.agent}'.")

    except HTTPException:
        raise
    except Exception as err:
        return AgentTestResponse(
            status="ERROR",
            agent=body.agent,
            configured_model=configured_model,
            verified_model=verified_meta,
            validation_status="ERROR",
            total_latency_ms=int((time.perf_counter() - t0) * 1000),
            error=str(err),
        )
