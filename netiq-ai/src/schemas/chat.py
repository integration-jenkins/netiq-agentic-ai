"""Chat request and response schemas for the NETIQ Agentic AI user interface.

Architecture Role:
------------------
This module defines the external contract for conversation requests and responses.
All user queries submitted via REST APIs, Streamlit UI, React frontend, or orchestration
graph pass through `ChatRequest`, and all final answers returned to callers conform
strictly to `ChatResponse`.

Key Guarantees:
---------------
1. Structured Data Alongside Text: Tabular data is returned in both `table` (rich UI contract)
   and `structured_data` (backward-compatible array) allowing UIs to render dynamic tables.
2. Mandatory Provenance: Contains `mode` ('MOCK' vs 'LIVE'), `sources`, `source_api`, and `evidence`
   to ensure UIs display synthetic data warning banners when running offline.
3. Explicit Failure Reporting: If an error occurs, `status` is marked 'ERROR' and details
   are provided in the `errors` array.
"""

import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.errors import StandardError
from src.schemas.evidence import EvidenceItem
from src.schemas.reports import ReportPagination


class MetricCard(BaseModel):
    """Single KPI or summary metric card rendered by the UI."""
    model_config = ConfigDict(frozen=True)

    label: str = Field(..., description="Human-readable metric label")
    value: int | float | str = Field(..., description="Deterministic metric value")


class ColumnMeta(BaseModel):
    """Metadata describing a single column in a dynamic report table."""
    model_config = ConfigDict(frozen=True)

    field: str = Field(..., description="JSON key in each row object")
    label: str = Field(..., description="Human-readable display header")
    type: str = Field(default="string", description="Data type hint ('string', 'integer', 'float', 'datetime')")


class TablePayload(BaseModel):
    """Dynamic tabular dataset with column metadata and server-side pagination."""
    model_config = ConfigDict(frozen=True)

    columns: list[ColumnMeta] = Field(default_factory=list, description="Ordered column definitions")
    rows: list[dict[str, Any]] = Field(default_factory=list, description="Current page of records")
    pagination: ReportPagination | None = Field(default=None, description="Pagination metadata")


class SourceReference(BaseModel):
    """Traceable source reference for a report or knowledge document."""
    model_config = ConfigDict(frozen=True)

    reportId: str | None = Field(default=None, description="Canonical report ID if applicable")
    reportName: str | None = Field(default=None, description="Human-readable report name")
    circle: str | None = Field(default=None, description="Authorized circle code")
    domain: str | None = Field(default=None, description="Telecom domain (RAN, MW, FTTH, etc.)")
    dataVersion: str | None = Field(default=None, description="Backend snapshot version if available")
    dataAsOf: str | None = Field(default=None, description="Actual source snapshot timestamp if available")
    mode: str = Field(default="MOCK", description="Execution mode provenance: 'MOCK' or 'LIVE'")
    docId: str | None = Field(default=None, description="Knowledge document ID if grounded in SOP/glossary")


class ExportInfo(BaseModel):
    """Metadata indicating whether a verified result can be exported to Excel."""
    model_config = ConfigDict(frozen=True)

    available: bool = Field(default=False, description="True if a verified tabular result is exportable")
    resultId: str | None = Field(default=None, description="Verified result ID for POST /v1/export")
    formats: list[str] = Field(default_factory=lambda: ["XLSX"], description="Supported export formats")


class ChatRequest(BaseModel):
    """User conversation request payload supporting both legacy and v1 UI contracts."""
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request tracing ID")
    session_id: str | None = Field(default=None, alias="sessionId", description="Conversation session ID")
    query: str = Field(..., min_length=1, max_length=4000, description="Natural language question submitted by user")
    circle: str | None = Field(default=None, description="Explicit telecom circle filter requested by user")
    filters: dict[str, Any] = Field(default_factory=dict, description="Optional structured filters (circle, domain, report_id)")
    pagination: dict[str, int] = Field(
        default_factory=lambda: {"page": 0, "size": 50},
        description="Requested page and page size"
    )
    user_id: str = Field(default="anonymous_user", description="Authenticated user principal identifier")
    user_roles: list[str] = Field(default_factory=lambda: ["viewer"], description="Security roles assigned to user")
    user_permitted_circles: list[str] = Field(
        default_factory=list,
        description="Authorized circle boundaries assigned to this user (e.g., ['DL', 'BR'])"
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, data: Any) -> Any:
        """Accept either `question` or `query`, and pull `circle` from `filters` if omitted."""
        if isinstance(data, dict):
            normalized = dict(data)
            if "query" not in normalized and "question" in normalized:
                normalized["query"] = normalized["question"]
            if "session_id" not in normalized and "sessionId" in normalized:
                normalized["session_id"] = normalized["sessionId"]
            filters = normalized.get("filters") or {}
            if not normalized.get("circle") and isinstance(filters, dict) and filters.get("circle"):
                normalized["circle"] = filters["circle"]
            return normalized
        return data


class ChatResponse(BaseModel):
    """Production-standardized chat response payload returned to Streamlit and React clients."""
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    request_id: str = Field(..., description="Correlating request tracking identifier")
    session_id: str | None = Field(default=None, description="Conversation session identifier")
    result_id: str | None = Field(default=None, description="Verified result identifier for pagination and export")
    status: str = Field(default="SUCCESS", description="Outcome: 'SUCCESS', 'EMPTY', 'ERROR', 'PARTIAL', 'AMBIGUOUS', 'NO_MATCH'")
    intent: str | None = Field(default=None, description="Classified intent (REPORT, KNOWLEDGE, COMPARISON, EXPORT, SQL)")
    agent: str | None = Field(default=None, description="Agent that handled the request")
    answer: str = Field(..., description="Deterministic natural language answer composed by orchestrator")

    # Rich UI contract fields
    metrics: list[MetricCard] = Field(default_factory=list, description="Summary KPI cards")
    table: TablePayload | None = Field(default=None, description="Dynamic table with columns, rows, and pagination")
    sources: list[SourceReference] = Field(default_factory=list, description="Traceable data or knowledge sources")
    export: ExportInfo | None = Field(default=None, description="Excel export availability metadata")
    execution_time_ms: int | None = Field(default=None, description="Total backend execution latency in milliseconds")
    warnings: list[str] = Field(default_factory=list, description="Operational warnings or data freshness notices")

    # Backward-compatible fields preserved for existing tests & adapters
    structured_data: list[dict[str, Any]] | None = Field(
        default=None,
        description="Structured tabular records for UI table rendering"
    )
    report_id: str | None = Field(default=None, description="Target report identifier if query resolved to a report")
    applied_filters: dict[str, Any] = Field(default_factory=dict, description="Normalized filters applied during retrieval")
    source_api: str | None = Field(default=None, description="Backend API path or endpoint template utilized")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Traceable evidence items supporting the answer")
    data_version: str | None = Field(default=None, description="Backend snapshot version identifier if provided")
    data_freshness: str | None = Field(default=None, description="Backend data freshness timestamp if provided")
    mode: str = Field(default="MOCK", description="Execution mode provenance: 'MOCK' or 'LIVE'")
    pagination: ReportPagination | None = Field(default=None, description="Pagination metadata if result is paginated")
    limitations: list[str] = Field(default_factory=list, description="Operational disclosures, synthetic warnings, or limits reached")
    errors: list[StandardError] = Field(default_factory=list, description="List of structured errors if execution failed")
