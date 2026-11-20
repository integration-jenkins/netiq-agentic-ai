"""Report metadata and verification schemas for NETIQ Agentic AI.

Architecture Role:
------------------
This module defines the schema for version-controlled report metadata definitions
stored in YAML files (`configs/reports/catalog.yaml` and domain directories `ran/`,
`mw/`, `ftth/`, `wireline/`, `audit/`, `ai/`).

Key Guarantees:
---------------
1. Multi-Dimensional Verification: Tracks independent verification statuses across
   8 distinct dimensions rather than assuming a single binary flag.
2. Field Identifier Separation: Preserves UI column IDs separately from Java DTO accessor
   keys and Oracle database column names.
3. No Silent Coercion: Data types and primary keys are never silently inferred from names.
4. Fail-Closed Production Eligibility: All source-derived entries are marked ineligible
   for LIVE execution (`production_eligible=False`) until verified by backend evidence.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class VerificationStatus(str, Enum):
    """Graduated status levels indicating verification maturity of metadata components.
    
    - SOURCE_DERIVED: Extracted directly from supplied Excel catalogue or CSV inventory.
    - VERIFIED: Formally confirmed against live Java backend HTTP response or database contract.
    - UNVERIFIED: Hypothetical or unconfirmed; pending backend inspection.
    - CONFLICT: Contradictory information identified across different worksheets or controllers.
    - NOT_AVAILABLE: Information does not exist in any supplied source documents.
    """
    SOURCE_DERIVED = "SOURCE_DERIVED"
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONFLICT = "CONFLICT"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class MetadataVerification(BaseModel):
    """Independent verification statuses across 8 distinct architectural dimensions.
    
    Prevents overclaiming readiness: A report may have a known API path (`SOURCE_DERIVED`)
    while its response JSON schema and pagination semantics remain completely `UNVERIFIED`.
    """
    model_config = ConfigDict(frozen=True)

    report_identity: VerificationStatus = Field(
        default=VerificationStatus.SOURCE_DERIVED,
        description="Verification of report business name and functional intent"
    )
    api_method_path: VerificationStatus = Field(
        default=VerificationStatus.SOURCE_DERIVED,
        description="Verification of candidate HTTP method and controller endpoint template"
    )
    field_mapping: VerificationStatus = Field(
        default=VerificationStatus.SOURCE_DERIVED,
        description="Verification of column IDs and DTO accessor mappings"
    )
    request_parameters: VerificationStatus = Field(
        default=VerificationStatus.SOURCE_DERIVED,
        description="Verification of supported query filters and request DTO body fields"
    )
    response_schema: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Verification of actual backend JSON response wrapper structure"
    )
    pagination: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Verification of total count calculations, page indices, and hasNext semantics"
    )
    business_rules: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Verification of circle restrictions and domain calculations"
    )
    authorization: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Verification of Spring Security roles and endpoint access rules"
    )


class ColumnMapping(BaseModel):
    """Column definition maintaining strict separation between UI, DTO, and DB.
    
    Ensures the system never confuses a frontend presentation label with a Java DTO field
    or an Oracle SQL table column.
    """
    model_config = ConfigDict(frozen=True)

    ui_column_id: str = Field(..., description="Frontend UI column identifier (e.g., 'cellName', 'Cabinet')")
    ui_header: str = Field(..., description="Human-readable column title displayed in UI (e.g., 'Cell Name')")
    dto_accessor: str = Field(..., description="Java DTO getter/field name (e.g., 'cellName', 'cabinet')")
    db_column_name: str | None = Field(default=None, description="Actual Oracle SQL column name (None until verified)")
    data_type: str | None = Field(default=None, description="Data type (never silently inferred; None until verified)")
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.SOURCE_DERIVED,
        description="Field-level verification status"
    )


class FilterMetadata(BaseModel):
    """Filter parameter metadata extracted from DTOs and filter guidance notes."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Filter parameter key (e.g., 'circle', 'vendor', 'technology')")
    type: str = Field(default="string", description="Parameter data type (string, date, integer)")
    required: bool = Field(default=False, description="Whether filter is mandatory on backend")
    guidance: str | None = Field(default=None, description="Operational notes on supported values and operators")


class ResponseMapping(BaseModel):
    """Metadata-driven dotted-path extractor configuration for response adapters.
    
    These keys configure where the response adapter will look inside the raw JSON payload.
    They are configuration settings, NOT claims about what the Java backend actually returns.
    """
    model_config = ConfigDict(frozen=True)

    rows_path: str = Field(default="data", description="Dotted path to record array in JSON (e.g., 'data', 'content')")
    total_path: str = Field(default="pagination.totalRecords", description="Dotted path to total count")
    page_path: str = Field(default="pagination.page", description="Dotted path to current page index")
    size_path: str = Field(default="pagination.size", description="Dotted path to page size")
    has_next_path: str = Field(default="hasNext", description="Dotted path to boolean hasNext indicator")
    status_path: str = Field(default="success", description="Dotted path to success boolean or status code")
    error_path: str = Field(default="message", description="Dotted path to error message or description")
    data_version_path: str | None = Field(default=None, description="Dotted path to snapshot version identifier")
    data_as_of_path: str | None = Field(default=None, description="Dotted path to data freshness timestamp")
    field_aliases: dict[str, str] = Field(default_factory=dict, description="Mapping from DTO accessor to UI column ID")


class ApiEndpointMetadata(BaseModel):
    """Candidate or approved backend HTTP API endpoint definition."""
    model_config = ConfigDict(frozen=True)

    method: str = Field(..., description="HTTP Method (GET or POST)")
    path: str = Field(..., description="Exact URL path (e.g., '/api/nodes/reports/4g')")
    path_template: str | None = Field(default=None, description="Normalized route template (e.g., '/api/nodes/reports/{reportType}')")
    request_dto: str | None = Field(default=None, description="Java request DTO class (e.g., 'ReportRequest', 'AuditReportRequest')")
    paged: bool = Field(default=True, description="Whether endpoint returns paginated results")
    page_size: int = Field(default=50, description="Default page size for queries")
    read_only: bool = Field(default=True, description="Safety classification: True for data retrieval operations")
    production_eligible: bool = Field(default=False, description="Whether endpoint is authorized for LIVE calls (False in Stage 1)")
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED, description="Contract verification level")


class SourceProvenance(BaseModel):
    """Audit traceability tracking the exact spreadsheet row and evidence source."""
    model_config = ConfigDict(frozen=True)

    worksheet: str = Field(..., description="Source Excel sheet name (e.g., '57 UI Reports', '64 Inventory Codes')")
    row_number: int = Field(..., description="1-based row number in source spreadsheet")
    source_evidence: str | None = Field(default=None, description="Java source class or document reference cited")
    notes: str | None = Field(default=None, description="Observations or ambiguity warnings from catalogue")


class ReportDefinition(BaseModel):
    """Complete, version-controlled report metadata specification.
    
    This model validates the YAML files written to `configs/reports/`.
    """
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique deterministic identifier (e.g., 'RAN_CELL_4G')")
    name: str = Field(..., description="Full report display title (e.g., 'RAN - Cell 4G')")
    description: str = Field(..., description="Business description of report purpose and data contents")
    domain: str = Field(..., description="Telecom domain category (e.g., 'RAN', 'MW', 'FTTH', 'Wireline', 'Audit')")
    report_code: str = Field(..., description="Backend Java report code (e.g., '4g', 'node-report')")
    file_path: str | None = Field(default=None, description="Relative path to domain YAML file")
    source_provenance: SourceProvenance = Field(..., description="Traceability back to origin documents")
    verification: MetadataVerification = Field(..., description="8-dimension verification status matrix")
    api: ApiEndpointMetadata | None = Field(default=None, description="Candidate API endpoint mapping if available")
    columns: list[ColumnMapping] = Field(default_factory=list, description="Ordered column definitions (from 1233 Column Mappings)")
    filters: list[FilterMetadata] = Field(default_factory=list, description="Known query filter parameters")
    response_mapping: ResponseMapping = Field(default_factory=ResponseMapping, description="Path extractors for response adapter")
    circle_scope: str = Field(default="server_side", description="Circle enforcement mechanism: 'server_side' (never client-trusted)")
    empty_result_message: str = Field(default="No Data Found!!", description="Backend message indicating zero matching records")
    notes: str | None = Field(default=None, description="Additional architectural or domain notes")
