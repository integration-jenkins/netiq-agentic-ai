"""Report metadata and verification schemas."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class VerificationStatus(str, Enum):
    """Status indicating the level of verification for metadata fields."""
    SOURCE_DERIVED = "SOURCE_DERIVED"
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONFLICT = "CONFLICT"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class MetadataVerification(BaseModel):
    """Independent verification statuses across all architectural dimensions."""
    model_config = ConfigDict(frozen=True)

    report_identity: VerificationStatus = VerificationStatus.SOURCE_DERIVED
    api_method_path: VerificationStatus = VerificationStatus.SOURCE_DERIVED
    field_mapping: VerificationStatus = VerificationStatus.SOURCE_DERIVED
    request_parameters: VerificationStatus = VerificationStatus.SOURCE_DERIVED
    response_schema: VerificationStatus = VerificationStatus.UNVERIFIED
    pagination: VerificationStatus = VerificationStatus.UNVERIFIED
    business_rules: VerificationStatus = VerificationStatus.UNVERIFIED
    authorization: VerificationStatus = VerificationStatus.UNVERIFIED


class ColumnMapping(BaseModel):
    """Column definition maintaining strict separation between UI, DTO, and DB."""
    model_config = ConfigDict(frozen=True)

    ui_column_id: str
    ui_header: str
    dto_accessor: str
    db_column_name: str | None = None
    data_type: str | None = None  # Never silently inferred; None/UNKNOWN until verified
    verification_status: VerificationStatus = VerificationStatus.SOURCE_DERIVED


class FilterMetadata(BaseModel):
    """Filter parameter metadata."""
    model_config = ConfigDict(frozen=True)

    name: str
    type: str = "string"
    required: bool = False
    guidance: str | None = None


class ResponseMapping(BaseModel):
    """Metadata-driven path extractors for response normalization.

    These are configuration values describing where fields reside in raw JSON,
    NOT assertions about live Java responses.
    """
    model_config = ConfigDict(frozen=True)

    rows_path: str = "data"
    total_path: str = "pagination.totalRecords"
    page_path: str = "pagination.page"
    size_path: str = "pagination.size"
    has_next_path: str = "hasNext"
    status_path: str = "success"
    error_path: str = "message"
    data_version_path: str | None = None
    data_as_of_path: str | None = None
    field_aliases: dict[str, str] = Field(default_factory=dict)


class ApiEndpointMetadata(BaseModel):
    """Candidate or approved API endpoint definition."""
    model_config = ConfigDict(frozen=True)

    method: str
    path: str
    path_template: str | None = None
    request_dto: str | None = None
    paged: bool = True
    page_size: int = 50
    read_only: bool = True
    production_eligible: bool = False
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED


class SourceProvenance(BaseModel):
    """Traceability back to origin spreadsheets and controller records."""
    model_config = ConfigDict(frozen=True)

    worksheet: str
    row_number: int
    source_evidence: str | None = None
    notes: str | None = None


class ReportDefinition(BaseModel):
    """Complete, version-controlled report metadata specification."""
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    description: str
    domain: str
    report_code: str
    source_provenance: SourceProvenance
    verification: MetadataVerification
    api: ApiEndpointMetadata | None = None
    columns: list[ColumnMapping] = Field(default_factory=list)
    filters: list[FilterMetadata] = Field(default_factory=list)
    response_mapping: ResponseMapping = Field(default_factory=ResponseMapping)
    circle_scope: str = "server_side"  # Server-enforced, never trusted from client text
    empty_result_message: str = "No Data Found!!"
    notes: str | None = None
