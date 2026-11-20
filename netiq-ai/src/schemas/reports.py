"""Report request and response schemas adhering to NETIQ standardized contracts.

Architecture Role:
------------------
This module defines the canonical Pydantic v2 data contracts for the Response
Standardization Layer. All raw API responses (from Java Spring Boot backend controllers
or offline synthetic MOCK fixtures) are transformed into these models.

Key Guarantees:
---------------
1. Zero Data Hallucination: The LLM never invents rows, counts, or dates.
2. Pagination Integrity: `returnedRecords` strictly matches `len(data)`.
3. Provenance Tracking: Every response carries source endpoint, mode (MOCK vs LIVE),
   and contract verification status.
4. Non-Tabular Separation: Metrics and network topology paths use dedicated typed models
   rather than an artificial `ReportPage`.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReportMode(str, Enum):
    """Execution mode of the report data retrieval.
    
    - MOCK: Response originates from offline synthetic test fixtures (safe, unverified contract).
    - LIVE: Response originates from the live NETIQ Java Spring Boot backend (verified contract only).
    """
    MOCK = "MOCK"
    LIVE = "LIVE"


class ReportStatus(str, Enum):
    """Outcome status of a report retrieval execution.
    
    - SUCCESS: Data successfully retrieved and normalized.
    - EMPTY: Query succeeded but backend returned zero matching records ("No Data Found!!").
    - ERROR: Query failed due to authorization, timeout, or backend errors.
    - PARTIAL: Multi-page retrieval capped at maximum safety ceiling (e.g. 1000 rows).
    """
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    ERROR = "ERROR"
    PARTIAL = "PARTIAL"


class ReportQuery(BaseModel):
    """Normalized query parameters requested by an AI agent or user.
    
    Standardizes page numbers, page limits, circle boundaries, and filters
    before dispatching to the NetIQ HTTP client or retrieval service.
    """
    model_config = ConfigDict(frozen=True)

    report_id: str = Field(..., description="Unique report identifier from catalog (e.g., 'RAN_CELL_4G')")
    circle: str | None = Field(default=None, description="Telecom circle identifier (e.g., 'DELHI', 'BR')")
    page: int = Field(default=0, ge=0, description="0-indexed page number (must be >= 0)")
    size: int = Field(default=50, gt=0, le=1000, description="Requested page size limit (positive integer)")
    filters: dict[str, Any] = Field(default_factory=dict, description="Report-specific filter criteria")
    columns: list[str] = Field(default_factory=list, description="Requested column projection")
    sort_by: str | None = Field(default=None, description="Sort field name")
    sort_direction: str | None = Field(default=None, description="Sort direction ('ASC' or 'DESC')")


class ReportPagination(BaseModel):
    """Standardized pagination metadata returned in report pages.
    
    Provides deterministic pagination state for UI rendering and agent navigation.
    """
    model_config = ConfigDict(frozen=True)

    page: int = Field(..., ge=0, description="0-indexed current page number")
    size: int = Field(..., gt=0, description="Requested page size limit")
    returnedRecords: int = Field(..., ge=0, description="Exact number of records returned in this page payload")
    totalRecords: int | None = Field(default=None, ge=0, description="Total matching records across all pages, if provided by backend")
    hasNext: bool = Field(..., description="True if subsequent pages are available from backend")

    @field_validator("totalRecords")
    @classmethod
    def validate_total_records(cls, v: int | None) -> int | None:
        """Enforce that totalRecords cannot be negative if provided."""
        if v is not None and v < 0:
            raise ValueError("totalRecords must be a non-negative integer when known.")
        return v


class ReportSource(BaseModel):
    """Source provenance and execution metadata for response verification.
    
    Carries full audit traceability so agents and human operators can verify
    where data came from and whether it represents synthetic or live production data.
    """
    model_config = ConfigDict(frozen=True)

    apiId: str = Field(..., description="Stable API identifier from allowlist (e.g., 'netiq_inventory_reports')")
    reportCode: str = Field(..., description="Backend Java report code (e.g., '4g', 'node-report')")
    endpoint: str = Field(..., description="Invoked backend HTTP endpoint path template")
    dataVersion: str | None = Field(default=None, description="Backend data snapshot version if provided")
    dataAsOf: str | None = Field(default=None, description="ISO timestamp of backend data freshness if provided")
    mode: ReportMode = Field(default=ReportMode.MOCK, description="Execution mode: MOCK or LIVE")
    contractStatus: str = Field(default="UNVERIFIED", description="Verification status of the API contract (e.g., 'UNVERIFIED', 'VERIFIED')")


class ReportPage(BaseModel):
    """Standardized paginated report page contract.
    
    This is the core target contract defined in the architecture specification.
    Guarantees structural consistency across all 57 NETIQ UI reports.
    """
    model_config = ConfigDict(frozen=True)

    reportId: str = Field(..., description="Unique report identifier matching configs/reports/catalog.yaml")
    domain: str = Field(..., description="Telecom domain category (e.g., 'RAN', 'MW', 'FTTH', 'Wireline', 'Audit')")
    status: ReportStatus = Field(default=ReportStatus.SUCCESS, description="Execution status")
    circle: str | None = Field(default=None, description="Telecom circle scope applied")
    data: list[dict[str, Any]] = Field(default_factory=list, description="Tabular record rows with normalized aliases")
    pagination: ReportPagination = Field(..., description="Pagination metadata")
    source: ReportSource = Field(..., description="Audit and provenance metadata")

    @model_validator(mode="after")
    def validate_payload_consistency(self) -> "ReportPage":
        """Validate logical consistency between data payload and pagination metadata.
        
        Rules:
        - `pagination.returnedRecords` must strictly equal `len(data)`.
        - `pagination.totalRecords` on page 0 cannot be less than `len(data)`.
        - Empty datasets on page 0 with hasNext=False are automatically marked EMPTY.
        """
        if self.pagination.returnedRecords != len(self.data):
            raise ValueError(
                f"Contradictory pagination: returnedRecords ({self.pagination.returnedRecords}) "
                f"does not match actual data count ({len(self.data)})."
            )

        if self.pagination.page == 0 and self.pagination.totalRecords is not None:
            if self.pagination.totalRecords < len(self.data):
                raise ValueError(
                    f"Contradictory pagination: totalRecords ({self.pagination.totalRecords}) "
                    f"is less than page 0 returnedRecords ({len(self.data)})."
                )

        if len(self.data) == 0 and self.status == ReportStatus.SUCCESS and not self.pagination.hasNext:
            object.__setattr__(self, "status", ReportStatus.EMPTY)

        return self


class MetricItem(BaseModel):
    """Single numeric or summary metric entry for dashboard endpoints."""
    model_config = ConfigDict(frozen=True)

    label: str = Field(..., description="Business metric label (e.g., 'Total Active Links')")
    value: float | int | str = Field(..., description="Calculated metric value")
    unit: str | None = Field(default=None, description="Optional measurement unit (e.g., 'hops', 'ms', '%')")


class NonPaginatedMetricResult(BaseModel):
    """Standardized typed model for non-paginated dashboard metrics and summaries.
    
    Used for endpoints like `/api/v1/stitching/summary` and `/api/v1/ai/daily-change/summary`
    to avoid wrapping simple metric dictionaries in an artificial `ReportPage`.
    """
    model_config = ConfigDict(frozen=True)

    reportId: str = Field(..., description="Unique report identifier")
    domain: str = Field(..., description="Telecom domain category")
    status: ReportStatus = Field(default=ReportStatus.SUCCESS, description="Execution status")
    metrics: list[MetricItem] = Field(default_factory=list, description="Extracted metric items")
    source: ReportSource = Field(..., description="Provenance metadata")


class StitchingPathResult(BaseModel):
    """Standardized typed model for end-to-end network stitching topology paths.
    
    Used for `/api/v1/stitching/paths` to represent graph-based route hops without
    forcing graph paths into a 2D tabular report model.
    """
    model_config = ConfigDict(frozen=True)

    serviceId: str = Field(..., description="Telecom circuit or service identifier")
    sourceSite: str = Field(..., description="Origin site ID")
    destinationSite: str = Field(..., description="Termination site ID")
    hopCount: int = Field(..., ge=0, description="Total intermediate hops in circuit")
    hops: list[dict[str, Any]] = Field(default_factory=list, description="Ordered hop node metadata")
    source: ReportSource = Field(..., description="Provenance metadata")
