"""End-to-end chat orchestration service connecting FastAPI /v1/chat to NETIQ agents.

Architecture Role:
------------------
Coordinates:
1. Circle & User Authorization (`AuthorizationService` + `CircleAccessPolicy`)
2. Follow-Up Session Resolution (`default_result_store`)
3. Intent Classification & Report Matching (`ReportSelector`, `KnowledgeAgent`)
4. Deterministic Data Retrieval (`ReportRetrievalService`)
5. Dynamic Column Metadata, Summary KPI Metrics, and Source Attribution
6. Result Persistence (`default_result_store`) for pagination and Excel export
"""

from __future__ import annotations

import re
import time
import uuid
from pathlib import Path
from typing import Any

from app.llms.knowledge_agent import KnowledgeDocument, default_knowledge_agent
from app.llms.report_selector import default_report_selector
from app.orchestrator.verify import ResponseVerifier
from src.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ColumnMeta,
    ExportInfo,
    MetricCard,
    SourceReference,
    TablePayload,
)
from src.schemas.errors import ErrorCode, StandardError
from src.schemas.reports import ReportPagination, ReportQuery, ReportStatus
from src.schemas.user import UserContext
from src.security.authorization import AuthorizationError, AuthorizationService
from src.security.circle_access import UnauthorizedCircleError
from src.session.result_store import (
    ResultAccessDeniedError,
    ResultNotFoundError,
    default_result_store,
)
from src.settings.env import PROJECT_ROOT, settings
from src.settings.loader import load_catalog_config
from src.tools.data_extraction.retrieval import ReportRetrievalService

_CIRCLE_ALIASES = {
    "bihar": "BR",
    "br": "BR",
    "delhi": "DL",
    "dl": "DL",
    "haryana": "HR",
    "hr": "HR",
    "mumbai": "MH",
    "maharashtra": "MH",
    "mh": "MH",
    "punjab": "PB",
    "pb": "PB",
    "karnataka": "KA",
    "ka": "KA",
    "tamilnadu": "TN",
    "tn": "TN",
}

_BUILTIN_KNOWLEDGE_DOCS = [
    KnowledgeDocument(
        doc_id="SOP-RAN-402",
        title="RAN Cell Availability and Incident Escalation",
        domain="RAN",
        content="SOP-RAN-402: eNodeB cell availability below 98.5% triggers Severity-2 and notification to the NOC RAN team.",
    ),
    KnowledgeDocument(
        doc_id="GLOSSARY-NETIQ-001",
        title="LTE / 5G Control Plane (CPLANE) vs User Plane (UPLANE)",
        domain="RAN",
        content=(
            "CPLANE (Control Plane) carries signaling traffic such as RRC, S1-AP, and NG-AP used for "
            "call setup, handover, and mobility management. UPLANE (User Plane) carries subscriber IP "
            "data payload over GTP-U tunnels between the eNodeB/gNodeB and the core gateway (SGW/UPF)."
        ),
    ),
]


def _infer_column_type(values: list[Any]) -> str:
    """Infer column type strictly from observed non-null row values."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "string"
    sample = non_null[0]
    if isinstance(sample, bool):
        return "boolean"
    if isinstance(sample, int):
        return "integer"
    if isinstance(sample, float):
        return "float"
    return "string"


def _humanize_label(field: str) -> str:
    """Convert camelCase or snake_case field name into a readable column header."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", field).replace("_", " ")
    return spaced.strip().title()


def _build_columns(rows: list[dict[str, Any]]) -> list[ColumnMeta]:
    """Build dynamic ColumnMeta list from actual API response rows."""
    if not rows:
        return []
    ordered_keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                ordered_keys.append(k)
    return [
        ColumnMeta(
            field=k,
            label=_humanize_label(k),
            type=_infer_column_type([r.get(k) for r in rows[:20]]),
        )
        for k in ordered_keys
    ]


def _extract_circles_from_text(text: str) -> list[str]:
    """Extract normalized telecom circle codes mentioned in text."""
    tokens = re.findall(r"[A-Za-z]+", text.lower())
    found: list[str] = []
    for tok in tokens:
        code = _CIRCLE_ALIASES.get(tok)
        if code and code not in found:
            found.append(code)
    return found


def _load_knowledge_docs() -> list[KnowledgeDocument]:
    """Load local markdown documents from knowledge_base/ plus built-in verified SOPs."""
    docs = list(_BUILTIN_KNOWLEDGE_DOCS)
    kb_dir = PROJECT_ROOT / "knowledge_base"
    if kb_dir.is_dir():
        for md_file in sorted(kb_dir.rglob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8").strip()
                if content:
                    docs.append(
                        KnowledgeDocument(
                            doc_id=md_file.stem.upper(),
                            title=md_file.stem.replace("_", " ").title(),
                            domain=md_file.parent.name.upper(),
                            content=content[:2000],
                        )
                    )
            except OSError:
                continue
    return docs


class ChatService:
    """Orchestrates chat queries into standardized, verified ChatResponse payloads."""

    def __init__(self, retrieval_service: ReportRetrievalService | None = None) -> None:
        self.retrieval = retrieval_service or ReportRetrievalService()
        self.auth_service = AuthorizationService()

    def _get_report_meta(self, report_id: str) -> dict[str, Any]:
        try:
            catalog = load_catalog_config()
            for r in catalog.get("reports", []):
                if r.get("id") == report_id:
                    return r
        except Exception:
            pass
        return {}

    async def process_chat(self, request: ChatRequest, user: UserContext) -> ChatResponse:
        """Process a user chat request and return a standardized ChatResponse."""
        t0 = time.perf_counter()
        session_id = request.session_id or f"session-{uuid.uuid4().hex[:10]}"
        query = request.query.strip()
        q_lower = query.lower()

        # Merge user context with request-level circle permissions if provided
        permitted_circles = user.permitted_circles or request.user_permitted_circles or ["*"]
        roles = user.roles or request.user_roles

        # Load/verify session ownership
        session_state = default_result_store.get_or_create_session(session_id, user.username)

        # Resolve requested circle (explicit param > filters > text extraction > session state)
        requested_circle = request.circle or (request.filters.get("circle") if request.filters else None)
        extracted_circles = _extract_circles_from_text(query)
        if not requested_circle and len(extracted_circles) == 1:
            requested_circle = extracted_circles[0]

        # 1. Handle Export Follow-Up ("Export the result", "Export to Excel")
        if any(w in q_lower for w in ("export", "download excel", "xlsx")) and session_state.last_result_id:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            return ChatResponse(
                request_id=request.request_id,
                session_id=session_id,
                result_id=session_state.last_result_id,
                status="SUCCESS",
                intent="EXPORT",
                agent="EXPORT_TOOL",
                answer=(
                    f"Verified result '{session_state.last_result_id}' is ready for Excel export. "
                    "Use the Export button or POST /v1/export to download the XLSX workbook."
                ),
                export=ExportInfo(available=True, resultId=session_state.last_result_id, formats=["XLSX"]),
                mode=settings.netiq_api_mode.value,
                execution_time_ms=elapsed_ms,
            )

        # 2. Handle Comparison Queries (e.g. "Compare RAN inventory between Delhi and Haryana")
        if "compare" in q_lower and (len(extracted_circles) >= 2 or (len(extracted_circles) == 1 and session_state.last_circle)):
            target_circles = (
                extracted_circles[:2]
                if len(extracted_circles) >= 2
                else [session_state.last_circle, extracted_circles[0]]
            )
            return await self._handle_comparison(
                request=request,
                user=user,
                session_id=session_id,
                circles=[c for c in target_circles if c],
                permitted_circles=permitted_circles,
                roles=roles,
                last_report_id=session_state.last_report_id,
                t0=t0,
            )

        # 3. Handle Follow-Up Filter on Previous Result (e.g. "Show only Ericsson")
        if session_state.last_result_id and any(
            q_lower.startswith(prefix) for prefix in ("show only ", "filter ", "only ")
        ):
            return await self._handle_followup_filter(
                request=request,
                user=user,
                session_id=session_id,
                last_result_id=session_state.last_result_id,
                permitted_circles=permitted_circles,
                t0=t0,
            )

        # 4. Handle Knowledge Questions
        if any(kw in q_lower for kw in ("explain", "difference between", "what is", "what happens", "sop-", "cplane", "uplane", "rsrp")):
            return await self._handle_knowledge(request, user, session_id, t0)

        # 5. Authorize Circle before Report Execution
        try:
            authorized_circle = self.auth_service.authorize_report_query(
                user_permitted_circles=permitted_circles,
                requested_circle=requested_circle,
                user_roles=roles,
            )
        except UnauthorizedCircleError as err:
            raise PermissionError(str(err)) from err
        except AuthorizationError as err:
            raise PermissionError(str(err)) from err

        # 6. Resolve Report ID (explicit filter > ReportSelector)
        explicit_report_id = (request.filters or {}).get("report_id")
        if explicit_report_id:
            report_id = explicit_report_id
            rep_meta = self._get_report_meta(report_id)
            if not rep_meta:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                return ChatResponse(
                    request_id=request.request_id,
                    session_id=session_id,
                    status="NO_MATCH",
                    intent="REPORT",
                    agent="REPORT_SELECTOR",
                    answer=f"Report ID '{report_id}' does not exist in the verified catalog.",
                    mode=settings.netiq_api_mode.value,
                    execution_time_ms=elapsed_ms,
                )
        else:
            sel = default_report_selector.select_report(query)
            if sel.status == "NO_MATCH":
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                return ChatResponse(
                    request_id=request.request_id,
                    session_id=session_id,
                    status="NO_MATCH",
                    intent="REPORT",
                    agent="REPORT_SELECTOR",
                    answer=sel.explanation or "No registered NETIQ report matched your question.",
                    mode=settings.netiq_api_mode.value,
                    execution_time_ms=elapsed_ms,
                )
            if sel.status == "AMBIGUOUS":
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                return ChatResponse(
                    request_id=request.request_id,
                    session_id=session_id,
                    status="AMBIGUOUS",
                    intent="REPORT",
                    agent="REPORT_SELECTOR",
                    answer=(
                        f"Your question matches multiple candidate reports: {', '.join(sel.candidate_ids)}. "
                        "Please select a specific report in the sidebar or clarify your request."
                    ),
                    mode=settings.netiq_api_mode.value,
                    warnings=[sel.explanation] if sel.explanation else [],
                    execution_time_ms=elapsed_ms,
                )
            report_id = sel.report_id
            rep_meta = self._get_report_meta(report_id)

        # 7. Retrieve Report Data via ReportRetrievalService
        page_num = int((request.pagination or {}).get("page", 0))
        page_size = int((request.pagination or {}).get("size", 50))
        applied_filters = dict(request.filters or {})
        if authorized_circle:
            applied_filters["circle"] = authorized_circle

        report_query = ReportQuery(
            report_id=report_id,
            circle=authorized_circle,
            filters=applied_filters,
            page=page_num,
            size=page_size,
        )

        page_result = await self.retrieval.get_single_page(
            query=report_query,
            user_permitted_circles=permitted_circles,
            correlation_id=request.request_id,
        )

        # Optional grouping if asked "grouped by vendor"
        rows = list(page_result.data)
        group_summary_metrics: list[MetricCard] = []
        if "grouped by vendor" in q_lower and rows and any("vendor" in r for r in rows):
            counts: dict[str, int] = {}
            for r in rows:
                v = str(r.get("vendor") or "Unknown")
                counts[v] = counts.get(v, 0) + 1
            rows = [{"vendor": v, "recordCount": c} for v, c in sorted(counts.items(), key=lambda x: -x[1])]
            group_summary_metrics.append(MetricCard(label="Distinct Vendors", value=len(rows)))

        columns = _build_columns(rows)
        total_records = page_result.pagination.totalRecords if page_result.pagination.totalRecords is not None else len(rows)

        metrics = [
            MetricCard(label="Returned Records", value=len(rows)),
            MetricCard(label="Total Records", value=total_records),
            *group_summary_metrics,
        ]

        report_name = rep_meta.get("name") or report_id
        domain = rep_meta.get("domain") or page_result.domain
        source_ref = SourceReference(
            reportId=report_id,
            reportName=report_name,
            circle=page_result.circle or authorized_circle,
            domain=domain,
            dataVersion=page_result.source.dataVersion,
            dataAsOf=page_result.source.dataAsOf,
            mode=page_result.source.mode.value,
        )

        saved = default_result_store.save_result(
            owner_username=user.username,
            report_id=report_id,
            report_name=report_name,
            circle=source_ref.circle,
            domain=domain,
            columns=columns,
            rows=rows,
            sources=[source_ref],
            applied_filters=applied_filters,
            data_version=source_ref.dataVersion,
            data_as_of=source_ref.dataAsOf,
            mode=source_ref.mode,
        )

        circle_str = f" for circle '{source_ref.circle}'" if source_ref.circle else ""
        if not rows:
            answer = f"No records found for '{report_name}'{circle_str}."
        else:
            answer = f"Retrieved {len(rows)} records for '{report_name}'{circle_str} (Total matching: {total_records})."

        warnings: list[str] = []
        if source_ref.mode == "MOCK":
            warnings.append("MOCK mode active: data is served from offline synthetic test fixtures.")
        if not source_ref.dataAsOf:
            warnings.append("Data date unavailable from source.")

        ResponseVerifier.verify_provenance_honesty(answer, source_ref.mode)
        evidence_item = ResponseVerifier.create_evidence_from_page(page_result)

        default_result_store.update_session(
            session_id=session_id,
            owner_username=user.username,
            user_question=query,
            assistant_answer=answer,
            report_id=report_id,
            report_name=report_name,
            circle=source_ref.circle,
            domain=domain,
            result_id=saved.result_id,
            filters=applied_filters,
        )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ChatResponse(
            request_id=request.request_id,
            session_id=session_id,
            result_id=saved.result_id,
            status=page_result.status.value,
            intent="REPORT",
            agent="REPORT_AGENT",
            answer=answer,
            metrics=metrics,
            table=TablePayload(
                columns=columns,
                rows=rows,
                pagination=ReportPagination(
                    page=page_num,
                    size=page_size,
                    returnedRecords=len(rows),
                    totalRecords=total_records,
                    hasNext=page_result.pagination.hasNext,
                ),
            ),
            sources=[source_ref],
            export=ExportInfo(available=True, resultId=saved.result_id, formats=["XLSX"]),
            execution_time_ms=elapsed_ms,
            warnings=warnings,
            structured_data=rows,
            report_id=report_id,
            applied_filters=applied_filters,
            source_api=page_result.source.endpoint,
            evidence=[evidence_item],
            data_version=source_ref.dataVersion,
            data_freshness=source_ref.dataAsOf,
            mode=source_ref.mode,
            pagination=page_result.pagination,
            limitations=warnings,
        )

    async def _handle_knowledge(
        self,
        request: ChatRequest,
        user: UserContext,
        session_id: str,
        t0: float,
    ) -> ChatResponse:
        docs = _load_knowledge_docs()
        q_tokens = set(re.findall(r"[a-z0-9-]+", request.query.lower()))
        scored: list[tuple[int, KnowledgeDocument]] = []
        for doc in docs:
            doc_tokens = set(re.findall(r"[a-z0-9-]+", f"{doc.doc_id} {doc.title} {doc.content}".lower()))
            overlap = len(q_tokens.intersection(doc_tokens))
            if overlap > 0:
                scored.append((overlap, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        top_docs = [d for _, d in scored[:2]]

        if not top_docs:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            return ChatResponse(
                request_id=request.request_id,
                session_id=session_id,
                status="NO_MATCH",
                intent="KNOWLEDGE",
                agent="KNOWLEDGE_AGENT",
                answer="INSUFFICIENT_EVIDENCE: No approved local knowledge documents matched your question.",
                mode=settings.netiq_api_mode.value,
                execution_time_ms=elapsed_ms,
            )

        # Deterministic threshold check first, then LLM if available, with safe grounded fallback
        det_sev, det_rule = default_knowledge_agent.evaluate_threshold_rule(
            request.query,
            "\n".join(d.content for d in top_docs),
        )
        try:
            k_ans = await default_knowledge_agent.answer_question(request.query, documents=top_docs)
            answer_text = k_ans.answer
            cited = k_ans.cited_sources
        except Exception:
            # Offline fallback when Ollama daemon is not running: return strictly grounded excerpt
            if det_sev:
                answer_text = f"[{top_docs[0].doc_id}] {det_rule}. {top_docs[0].content}"
            else:
                answer_text = f"[{top_docs[0].doc_id}] {top_docs[0].content}"
            cited = [top_docs[0].doc_id]

        sources = [
            SourceReference(
                reportId=None,
                reportName=d.title,
                domain=d.domain,
                mode=settings.netiq_api_mode.value,
                docId=d.doc_id,
            )
            for d in top_docs if d.doc_id in cited
        ]

        default_result_store.update_session(
            session_id=session_id,
            owner_username=user.username,
            user_question=request.query,
            assistant_answer=answer_text,
        )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ChatResponse(
            request_id=request.request_id,
            session_id=session_id,
            status="SUCCESS",
            intent="KNOWLEDGE",
            agent="KNOWLEDGE_AGENT",
            answer=answer_text,
            sources=sources,
            mode=settings.netiq_api_mode.value,
            execution_time_ms=elapsed_ms,
        )

    async def _handle_followup_filter(
        self,
        request: ChatRequest,
        user: UserContext,
        session_id: str,
        last_result_id: str,
        permitted_circles: list[str],
        t0: float,
    ) -> ChatResponse:
        try:
            prev = default_result_store.get_result(
                result_id=last_result_id,
                username=user.username,
                is_admin=user.is_admin,
                permitted_circles=permitted_circles,
            )
        except (ResultNotFoundError, ResultAccessDeniedError) as err:
            raise PermissionError(str(err)) from err

        # Extract filter keyword (e.g., "show only ericsson" -> "ericsson")
        filter_term = re.sub(r"^(show\s+only|filter\s+by|filter|only)\s+", "", request.query.strip(), flags=re.IGNORECASE).strip().lower()
        filtered_rows = [
            r for r in prev.rows
            if any(filter_term in str(v).lower() for v in r.values() if v is not None)
        ]

        new_filters = dict(prev.applied_filters)
        new_filters["followup_filter"] = filter_term

        saved = default_result_store.save_result(
            owner_username=user.username,
            report_id=prev.report_id,
            report_name=prev.report_name,
            circle=prev.circle,
            domain=prev.domain,
            columns=prev.columns,
            rows=filtered_rows,
            sources=prev.sources,
            applied_filters=new_filters,
            data_version=prev.data_version,
            data_as_of=prev.data_as_of,
            mode=prev.mode,
        )

        answer = f"Filtered '{prev.report_name}' for '{filter_term}': {len(filtered_rows)} matching records."
        default_result_store.update_session(
            session_id=session_id,
            owner_username=user.username,
            user_question=request.query,
            assistant_answer=answer,
            result_id=saved.result_id,
            filters=new_filters,
        )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ChatResponse(
            request_id=request.request_id,
            session_id=session_id,
            result_id=saved.result_id,
            status="SUCCESS" if filtered_rows else "EMPTY",
            intent="REPORT",
            agent="REPORT_AGENT",
            answer=answer,
            metrics=[
                MetricCard(label="Filtered Records", value=len(filtered_rows)),
                MetricCard(label="Previous Records", value=len(prev.rows)),
            ],
            table=TablePayload(
                columns=prev.columns,
                rows=filtered_rows,
                pagination=ReportPagination(
                    page=0,
                    size=50,
                    returnedRecords=len(filtered_rows),
                    totalRecords=len(filtered_rows),
                    hasNext=False,
                ),
            ),
            sources=prev.sources,
            export=ExportInfo(available=True, resultId=saved.result_id, formats=["XLSX"]),
            mode=prev.mode,
            structured_data=filtered_rows,
            report_id=prev.report_id,
            applied_filters=new_filters,
            execution_time_ms=elapsed_ms,
        )

    async def _handle_comparison(
        self,
        request: ChatRequest,
        user: UserContext,
        session_id: str,
        circles: list[str],
        permitted_circles: list[str],
        roles: list[str],
        last_report_id: str | None,
        t0: float,
    ) -> ChatResponse:
        # Authorize every requested circle independently
        authorized_circles: list[str] = []
        for c in circles:
            auth_c = self.auth_service.authorize_report_query(
                user_permitted_circles=permitted_circles,
                requested_circle=c,
                user_roles=roles,
            )
            if auth_c:
                authorized_circles.append(auth_c)

        sel = default_report_selector.select_report(request.query)
        report_id = (
            (request.filters or {}).get("report_id")
            or (sel.report_id if sel.status == "MATCH" else None)
            or last_report_id
            or "RAN_CELL_4G"
        )
        rep_meta = self._get_report_meta(report_id)
        report_name = rep_meta.get("name") or report_id
        domain = rep_meta.get("domain")

        comparison_rows: list[dict[str, Any]] = []
        sources: list[SourceReference] = []
        metrics: list[MetricCard] = []

        for c in authorized_circles:
            q = ReportQuery(report_id=report_id, circle=c, filters={"circle": c}, page=0, size=50)
            page_res = await self.retrieval.get_single_page(q, user_permitted_circles=permitted_circles)
            total = page_res.pagination.totalRecords if page_res.pagination.totalRecords is not None else len(page_res.data)
            comparison_rows.append({
                "circle": c,
                "reportId": report_id,
                "returnedRecords": len(page_res.data),
                "totalRecords": total,
                "dataVersion": page_res.source.dataVersion,
            })
            metrics.append(MetricCard(label=f"{c} Total", value=total))
            sources.append(
                SourceReference(
                    reportId=report_id,
                    reportName=report_name,
                    circle=c,
                    domain=domain,
                    dataVersion=page_res.source.dataVersion,
                    dataAsOf=page_res.source.dataAsOf,
                    mode=page_res.source.mode.value,
                )
            )

        columns = _build_columns(comparison_rows)
        mode_val = sources[0].mode if sources else settings.netiq_api_mode.value
        saved = default_result_store.save_result(
            owner_username=user.username,
            report_id=report_id,
            report_name=f"{report_name} (Comparison)",
            circle=",".join(authorized_circles),
            domain=domain,
            columns=columns,
            rows=comparison_rows,
            sources=sources,
            applied_filters={"circles": authorized_circles},
            data_version=sources[0].dataVersion if sources else None,
            data_as_of=sources[0].dataAsOf if sources else None,
            mode=mode_val,
        )

        answer = f"Comparison of '{report_name}' across circles: {', '.join(authorized_circles)}."
        default_result_store.update_session(
            session_id=session_id,
            owner_username=user.username,
            user_question=request.query,
            assistant_answer=answer,
            report_id=report_id,
            report_name=report_name,
            circle=authorized_circles[0] if authorized_circles else None,
            domain=domain,
            result_id=saved.result_id,
        )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ChatResponse(
            request_id=request.request_id,
            session_id=session_id,
            result_id=saved.result_id,
            status="SUCCESS",
            intent="COMPARISON",
            agent="COMPARISON_AGENT",
            answer=answer,
            metrics=metrics,
            table=TablePayload(
                columns=columns,
                rows=comparison_rows,
                pagination=ReportPagination(
                    page=0,
                    size=50,
                    returnedRecords=len(comparison_rows),
                    totalRecords=len(comparison_rows),
                    hasNext=False,
                ),
            ),
            sources=sources,
            export=ExportInfo(available=True, resultId=saved.result_id, formats=["XLSX"]),
            mode=mode_val,
            structured_data=comparison_rows,
            report_id=report_id,
            execution_time_ms=elapsed_ms,
        )


default_chat_service = ChatService()
