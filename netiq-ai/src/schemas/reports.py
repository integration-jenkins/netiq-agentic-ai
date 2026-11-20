"""Report request and response schemas adhering to NETIQ standardized contract."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReportMode(str, Enum):
    MOCK = "MOCK"
    LIVE = "LIVE"


class ReportStatus(str, Enum):
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    ERROR = "ERROR"
    PARTIAL = "PARTIAL"


class ReportQuery(BaseModel):
    """Normalized query parameters for report retrieval."""
    model_config = ConfigDict(frozen=True)

    report_id: str = Field(..., description="Unique report identifier from catalog")
    circle: str | None = Field(default=None, description="Telecom circle identifier")
    page: int = Field(default=0, ge=0, description="0-indexed page number")
    size: int = Field(default=50, gt=0, le=1000, description="Requested page size")
    filters: dict[str, Any] = Field(default_factory=dict, description="Report-specific filter criteria")
    columns: list[str] = Field(default_factory=list, description="Requested column projection")
    sort_by: str | None = Field(default=None, description="Sort field name")
    sort_direction: str | None = Field(default=None, description="ASC or DESC")


class ReportPagination(BaseModel):
    """Standardized pagination metadata."""
    model_config = ConfigDict(frozen=True)

    page: int = Field(..., ge=0, description="0-indexed current page")
    size: int = Field(..., gt=0, description="Page size limit")
    returnedRecords: int = Field(..., ge=0, description="Records present in current page payload")
    totalRecords: int | None = Field(default=None, ge=0, description="Total matching records if known")
    hasNext: bool = Field(..., description="Whether subsequent pages are available")

    @field_validator("totalRecords")
    @classmethod
    def validate_total_records(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("totalRecords must be a non-negative integer when known.")
        return v


class ReportSource(BaseModel):
    """Source provenance and execution metadata for response verification."""
    model_config = ConfigDict(frozen=True)

    apiId: str = Field(..., description="Stable API identifier from allowlist")
    reportCode: str = Field(..., description="Backend report code")
    endpoint: str = Field(..., description="Invoked backend endpoint path")
    dataVersion: str | None = Field(default=None, description="Backend data snapshot version if provided")
    dataAsOf: str | None = Field(default=None, description="Timestamp of backend data freshness if provided")
    mode: ReportMode = Field(default=ReportMode.MOCK, description="MOCK or LIVE execution mode")
    contractStatus: str = Field(default="UNVERIFIED", description="Verification status of the API contract")


class ReportPage(BaseModel):
    """Standardized paginated report page contract."""
    model_config = ConfigDict(frozen=True)

    reportId: str = Field(..., description="Unique report identifier")
    domain: str = Field(..., description="Telecom domain (RAN, MW, FTTH, etc.)")
    status: ReportStatus = Field(default=ReportStatus.SUCCESS, description="Query execution status")
    circle: str | None = Field(default=None, description="Circle scope applied")
    data: list[dict[str, Any]] = Field(default_factory=list, description="Tabular record rows")
    pagination: ReportPagination = Field(..., description="Pagination metadata")
    source: ReportSource = Field(..., description="Provenance information")

    @model_validator(mode="after")
    def validate_payload_consistency(self) -> "ReportPage":
        # returnedRecords must strictly match the length of the returned data array
        if self.pagination.returnedRecords != len(self.data):
            raise ValueError(
                f"Contradictory pagination: returnedRecords ({self.pagination.returnedRecords}) "
                f"does not match actual data count ({len(self.data)})."
            )

        # totalRecords if provided must be >= returnedRecords on page 0
        if self.pagination.page == 0 and self.pagination.totalRecords is not None:
            if self.pagination.totalRecords < len(self.data):
                raise ValueError(
                    f"Contradictory pagination: totalRecords ({self.pagination.totalRecords}) "
                    f"is less than page 0 returnedRecords ({len(self.data)})."
                )

        # If data is empty and page is 0, auto-classify as EMPTY if SUCCESS
        if len(self.data) == 0 and self.status == ReportStatus.SUCCESS and not self.pagination.hasNext:
            object.__setattr__(self, "status", ReportStatus.EMPTY)

        return self


class MetricItem(BaseModel):
    """Single numeric or summary metric."""
    model_config = ConfigDict(frozen=True)

    label: str
    value: float | int | str
    unit: str | None = None


class NonPaginatedMetricResult(BaseModel):
    """Standardized typed model for non-paginated dashboard metrics and summaries."""
    model_config = ConfigDict(frozen=True)

    reportId: str
    domain: str
    status: ReportStatus = ReportStatus.SUCCESS
    metrics: list[MetricItem] = Field(default_factory=list)
    source: ReportSource


class StitchingPathResult(BaseModel):
    """Standardized typed model for end-to-end network stitching paths."""
    model_config = ConfigDict(frozen=True)

    serviceId: str
    sourceSite: str
    destinationSite: str
    hopCount: int = Field(..., ge=0)
    hops: list[dict[str, Any]] = Field(default_factory=list)
    source: ReportSource
