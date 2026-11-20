"""Final deterministic response composition adhering to ChatResponse schema."""

from typing import Any
from app.orchestrator.verify import ResponseVerifier
from src.schemas.chat import ChatRequest, ChatResponse
from src.schemas.errors import ErrorCode, StandardError
from src.schemas.reports import ReportPage, ReportStatus


class ChatComposer:
    """Deterministic response composer; avoids unsupported claims and hallucinations."""

    @staticmethod
    def compose_report_response(
        request: ChatRequest,
        page: ReportPage,
        report_name: str | None = None,
        applied_filters: dict[str, Any] | None = None,
        limitations: list[str] | None = None,
    ) -> ChatResponse:
        """Compose standardized chat response from ReportPage."""
        filters = applied_filters or {}
        limits = list(limitations or [])

        # Generate evidence
        evidence_item = ResponseVerifier.create_evidence_from_page(page)
        evidence_list = [evidence_item]

        # Determine textual answer deterministically
        display_name = report_name or page.reportId
        circle_str = f" for circle '{page.circle}'" if page.circle else ""

        if page.status == ReportStatus.EMPTY:
            answer = f"No records found for report '{display_name}'{circle_str}. Backend returned empty result."
        elif page.status == ReportStatus.PARTIAL:
            answer = (
                f"Retrieved partial results ({page.pagination.returnedRecords} records) for report '{display_name}'{circle_str}. "
                f"Total matching records: {page.pagination.totalRecords if page.pagination.totalRecords is not None else 'unknown'}. "
                "Retrieval capped at maximum configured limits."
            )
            limits.append("Results were capped at safety ceiling; export workflow recommended for full dataset.")
        else:
            total_str = (
                f" (Total matching records: {page.pagination.totalRecords})"
                if page.pagination.totalRecords is not None
                else ""
            )
            answer = (
                f"Successfully retrieved {page.pagination.returnedRecords} records for report '{display_name}'{circle_str}{total_str}."
            )

        # MOCK provenance banner
        if page.source.mode.value == "MOCK":
            limits.append("Synthetic MOCK mode active: Data is generated from approved local test fixtures.")
            answer = f"[MOCK DATA] {answer}\n*Note: Live NETIQ Java API contract is unverified.*"

        # Verify provenance honesty
        ResponseVerifier.verify_provenance_honesty(answer=answer, mode=page.source.mode.value)

        return ChatResponse(
            request_id=request.request_id,
            status=page.status.value,
            answer=answer,
            structured_data=page.data,
            report_id=page.reportId,
            applied_filters=filters,
            source_api=page.source.endpoint,
            evidence=evidence_list,
            data_version=page.source.dataVersion,
            data_freshness=page.source.dataAsOf,
            mode=page.source.mode.value,
            pagination=page.pagination,
            limitations=limits,
            errors=[],
        )

    @staticmethod
    def compose_error_response(
        request: ChatRequest,
        error_code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        report_id: str | None = None,
    ) -> ChatResponse:
        """Compose standardized error response."""
        std_error = StandardError(
            code=error_code,
            message=message,
            details=details or {},
        )

        return ChatResponse(
            request_id=request.request_id,
            status="ERROR",
            answer=f"Error executing request: {message}",
            structured_data=None,
            report_id=report_id,
            applied_filters={},
            source_api=None,
            evidence=[],
            data_version=None,
            data_freshness=None,
            mode="MOCK",
            pagination=None,
            limitations=[],
            errors=[std_error],
        )
