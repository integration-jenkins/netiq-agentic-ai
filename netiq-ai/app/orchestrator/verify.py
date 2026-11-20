"""Verification layer ensuring factual consistency, deterministic math, and provenance honesty."""

from typing import Any
from src.schemas.evidence import EvidenceItem, EvidenceType
from src.schemas.reports import ReportPage


class VerificationError(Exception):
    """Raised when an unverified claim or factual contradiction is detected."""
    pass


class ResponseVerifier:
    """Deterministic verifier for NETIQ agent outputs."""

    @staticmethod
    def create_evidence_from_page(page: ReportPage, citation: str | None = None) -> EvidenceItem:
        """Extract verified evidence record from a standardized ReportPage."""
        sample_rows = page.data[:3] if page.data else []
        return EvidenceItem(
            evidence_type=EvidenceType.REPORT_PAGE,
            report_id=page.reportId,
            endpoint=page.source.endpoint,
            mode=page.source.mode.value,
            record_count=page.pagination.returnedRecords,
            sample_records=sample_rows,
            data_version=page.source.dataVersion,
            data_as_of=page.source.dataAsOf,
            contract_status=page.source.contractStatus,
            citation=citation or f"NETIQ Report {page.reportId} via {page.source.endpoint}",
        )

    @staticmethod
    def verify_provenance_honesty(answer: str, mode: str) -> None:
        """Ensure synthetic MOCK answers are not falsely represented as live data."""
        lower_ans = answer.lower()
        if mode.upper() == "MOCK":
            # If in MOCK mode, the answer must not claim to be verified live production data
            if "live production data" in lower_ans or "verified live telecom" in lower_ans:
                raise VerificationError("Integrity violation: MOCK results cannot be claimed as live production data.")
