"""Final deterministic response composition adhering to ChatResponse schema.

Architecture Role:
------------------
This module composes the final user-facing `ChatResponse` payload.
It guarantees:
1. Deterministic Answers: Response text is composed directly from validated data
   models (`ReportPage`), avoiding LLM arithmetic errors or fabricated records.
2. Mandatory Provenance Disclaimers: Prepend/append clear notices whenever responses
   are generated in MOCK mode from offline synthetic fixtures.
3. Clean Error Formatting: Converts exceptions into standardized `ChatResponse` objects
   with `status="ERROR"` and structured error details.
"""

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
        """Compose standardized chat response from ReportPage.
        
        Args:
            request: Original user ChatRequest.
            page: Normalized ReportPage resulting from query.
            report_name: Human-friendly report name (e.g., 'RAN Node Inventory').
            applied_filters: Normalized dictionary of filters applied during query.
            limitations: Optional list of limitations or truncation notices.
            
        Returns:
            ChatResponse: Canonical response payload.
        """
        filters = applied_filters or {}
        limits = list(limitations or [])

        # Generate verifiable evidence record
        evidence_item = ResponseVerifier.create_evidence_from_page(page)
        evidence_list = [evidence_item]

        # Determine textual answer deterministically from model data
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

        # Append explicit MOCK mode provenance banner when running offline
        if page.source.mode.value == "MOCK":
            limits.append("Synthetic MOCK mode active: Data is generated from approved local test fixtures.")
            answer = f"[MOCK DATA] {answer}\n*Note: Live NETIQ Java API contract is unverified.*"

        # Verify provenance honesty before returning
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
        """Compose standardized error response from an exception or failure.
        
        Args:
            request: Original user ChatRequest.
            error_code: Machine-readable ErrorCode.
            message: Descriptive error explanation.
            details: Contextual error details or parameters.
            report_id: Optional report ID attempted.
            
        Returns:
            ChatResponse: Standardized response payload with status="ERROR".
        """
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
