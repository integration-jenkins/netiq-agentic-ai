"""Metadata-driven response normalization adapter engine for NETIQ Agentic AI.

Architecture Role:
------------------
This module is the core normalization engine. Different Java Spring Boot telecom
controllers return JSON responses with varying wrapper structures, field keys, and
pagination schemes.

Instead of writing brittle, hardcoded parsing logic for every report, this engine uses
metadata configurations (`response_mapping` in each report definition) to extract,
remap, and validate data into canonical Pydantic models (`ReportPage`, `NonPaginatedMetricResult`).

Key Guarantees:
---------------
1. No Code Execution: Uses a safe dotted-path parser; never executes arbitrary expressions.
2. Field Alias Remapping: Reconciles divergence between frontend UI column IDs and
   backend Java DTO accessors.
3. Clean Empty-State Handling: Normalizes "No Data Found!!" payloads into `ReportStatus.EMPTY`
   without throwing exceptions.
4. Identical Pipeline for MOCK & LIVE: Offline synthetic fixtures pass through the exact
   same normalization code paths as live backend data.
"""

from typing import Any
from src.schemas.errors import ErrorCode, StandardError
from src.schemas.metadata import ReportDefinition
from src.schemas.reports import (
    MetricItem,
    NonPaginatedMetricResult,
    ReportMode,
    ReportPage,
    ReportPagination,
    ReportSource,
    ReportStatus,
    StitchingPathResult,
)


class MalformedResponseError(Exception):
    """Raised when backend response does not conform to expected JSON schema."""
    pass


def extract_dotted_path(data: Any, path: str | None, default: Any = None) -> Any:
    """Safely traverse a nested dictionary or list using dotted syntax.

    Features:
    - Traverses dictionaries using string keys (e.g., 'pagination.totalRecords').
    - Traverses lists using integer indices (e.g., 'items.0.name').
    - Strictly avoids eval() or arbitrary Python expression execution.
    - Returns `default` safely if any key along the path is missing or None.
    
    Args:
        data: Root dictionary or list payload.
        path: Dot-separated path string (e.g., 'data.items').
        default: Fallback value returned if path is not found.
        
    Returns:
        Any: Value at the specified path, or `default`.
    """
    if not path or data is None:
        return default
    curr = data
    for part in path.split("."):
        if isinstance(curr, dict):
            curr = curr.get(part)
        elif isinstance(curr, (list, tuple)):
            if part.isdigit():
                idx = int(part)
                curr = curr[idx] if 0 <= idx < len(curr) else None
            else:
                return default
        else:
            return default
        if curr is None:
            return default
    return curr


class BaseResponseAdapter:
    """Base response adapter providing core normalization utilities.
    
    Provides shared logic for field alias mapping, source provenance generation,
    and metadata lookup.
    """

    def __init__(self, report_def: ReportDefinition | dict[str, Any] | None = None) -> None:
        """Initialize adapter with report metadata.
        
        Args:
            report_def: Pydantic ReportDefinition or raw metadata dictionary.
        """
        if isinstance(report_def, ReportDefinition):
            self.report_def = report_def
            self.report_dict = report_def.model_dump()
        elif isinstance(report_def, dict):
            self.report_dict = report_def
            self.report_def = None
        else:
            self.report_dict = {}
            self.report_def = None

        self.mapping = self.report_dict.get("response_mapping", {})

    def normalize_row_aliases(self, row: dict[str, Any]) -> dict[str, Any]:
        """Normalize row dictionary keys according to configured field aliases.
        
        For example, if Java DTO returns `cabinet` but UI expects `Cabinet`,
        the alias configuration maps `cabinet` -> `Cabinet`.
        """
        aliases = self.mapping.get("field_aliases", {})
        if not aliases:
            return row
        normalized = {}
        for k, v in row.items():
            normalized[aliases.get(k, k)] = v
        return normalized

    def build_source(
        self,
        endpoint: str,
        report_code: str,
        api_id: str = "generic_report_api",
        mode: ReportMode = ReportMode.MOCK,
        contract_status: str = "UNVERIFIED",
        data_version: str | None = None,
        data_as_of: str | None = None,
    ) -> ReportSource:
        """Construct standard provenance and audit tracking object."""
        return ReportSource(
            apiId=api_id,
            reportCode=report_code,
            endpoint=endpoint,
            dataVersion=data_version,
            dataAsOf=data_as_of,
            mode=mode,
            contractStatus=contract_status,
        )


class PaginatedInventoryResponseAdapter(BaseResponseAdapter):
    """Adapter for paginated inventory, configuration, and parameter reports.
    
    Handles standard generic endpoints such as `/api/nodes/reports/{reportType}`.
    Extracts tabular record rows, normalizes pagination indices, and determines
    empty vs success status.
    """

    def adapt(
        self,
        raw_json: dict[str, Any],
        report_id: str,
        domain: str,
        endpoint: str,
        report_code: str,
        mode: ReportMode = ReportMode.MOCK,
        circle: str | None = None,
        contract_status: str = "UNVERIFIED",
        query_page: int = 0,
        query_size: int = 50,
    ) -> ReportPage:
        """Transform raw JSON response into a validated ReportPage.
        
        Args:
            raw_json: Parsed response JSON from HTTP client or MOCK fixture.
            report_id: Unique catalog report identifier.
            domain: Telecom domain name.
            endpoint: URL path invoked.
            report_code: Backend report code.
            mode: MOCK or LIVE execution mode.
            circle: Circle filter applied.
            contract_status: Contract verification level.
            query_page: Requested page number (fallback).
            query_size: Requested page size (fallback).
            
        Returns:
            ReportPage: Canonical validated response.
            
        Raises:
            MalformedResponseError: If JSON structure does not match expected schema.
        """
        if not isinstance(raw_json, dict):
            raise MalformedResponseError(f"Expected JSON object response, got {type(raw_json).__name__}")

        # Check for status and error message
        status_path = self.mapping.get("status_path", "success")
        error_path = self.mapping.get("error_path", "message")
        
        status_val = extract_dotted_path(raw_json, status_path)
        message_val = extract_dotted_path(raw_json, error_path, "")

        # Check for standard "No Data Found!!" pattern
        empty_marker = self.report_dict.get("empty_result_message", "No Data Found!!")
        is_empty_message = isinstance(message_val, str) and empty_marker.lower() in message_val.lower()

        # Extract record rows from configured path
        rows_path = self.mapping.get("rows_path", "data")
        raw_rows = extract_dotted_path(raw_json, rows_path)

        if raw_rows is None:
            if is_empty_message or status_val is False:
                raw_rows = []
            else:
                raise MalformedResponseError(f"Rows path '{rows_path}' was not found in response.")

        if not isinstance(raw_rows, list):
            raise MalformedResponseError(f"Expected rows at '{rows_path}' to be a list, got {type(raw_rows).__name__}")

        # Normalize field aliases on all returned rows
        normalized_rows = [self.normalize_row_aliases(r) if isinstance(r, dict) else r for r in raw_rows]

        # Extract pagination fields using safe dotted-paths
        total_path = self.mapping.get("total_path", "pagination.totalRecords")
        page_path = self.mapping.get("page_path", "pagination.page")
        size_path = self.mapping.get("size_path", "pagination.size")
        has_next_path = self.mapping.get("has_next_path", "hasNext")

        total_records = extract_dotted_path(raw_json, total_path)
        if total_records is None:
            # Check secondary fallback paths for alternative backend wrappers
            total_records = extract_dotted_path(raw_json, "totalRecords") or extract_dotted_path(raw_json, "total")

        if total_records is not None:
            try:
                total_records = int(total_records)
            except (ValueError, TypeError):
                total_records = None

        page_val = extract_dotted_path(raw_json, page_path, query_page)
        size_val = extract_dotted_path(raw_json, size_path, query_size)
        has_next_val = extract_dotted_path(raw_json, has_next_path)

        # Deterministically infer hasNext if total_records is known
        if has_next_val is None:
            if total_records is not None:
                has_next_val = ((page_val + 1) * size_val) < total_records
            else:
                has_next_val = False
        else:
            has_next_val = bool(has_next_val)

        returned_count = len(normalized_rows)

        pagination = ReportPagination(
            page=max(0, int(page_val) if page_val is not None else query_page),
            size=max(1, int(size_val) if size_val is not None else query_size),
            returnedRecords=returned_count,
            totalRecords=total_records,
            hasNext=has_next_val,
        )

        # Extract data version and freshness if paths are configured
        data_version_path = self.mapping.get("data_version_path")
        data_as_of_path = self.mapping.get("data_as_of_path")
        data_version = extract_dotted_path(raw_json, data_version_path) if data_version_path else None
        data_as_of = extract_dotted_path(raw_json, data_as_of_path) if data_as_of_path else None

        source = self.build_source(
            endpoint=endpoint,
            report_code=report_code,
            api_id=f"netiq_{report_code}",
            mode=mode,
            contract_status=contract_status,
            data_version=str(data_version) if data_version else None,
            data_as_of=str(data_as_of) if data_as_of else None,
        )

        rep_status = ReportStatus.EMPTY if (returned_count == 0 or is_empty_message) else ReportStatus.SUCCESS

        return ReportPage(
            reportId=report_id,
            domain=domain,
            status=rep_status,
            circle=circle,
            data=normalized_rows,
            pagination=pagination,
            source=source,
        )


class PaginatedAuditResponseAdapter(PaginatedInventoryResponseAdapter):
    """Adapter for audit report responses (e.g. AuditReportRequest endpoints).
    
    Inherits paginated normalization behavior with specialized audit handling.
    """
    pass


class NonPaginatedMetricResponseAdapter(BaseResponseAdapter):
    """Adapter for non-paginated metric summaries (e.g. daily-change, stitching summary).
    
    Transforms key-value summary objects into `NonPaginatedMetricResult`.
    """

    def adapt(
        self,
        raw_json: dict[str, Any],
        report_id: str,
        domain: str,
        endpoint: str,
        mode: ReportMode = ReportMode.MOCK,
    ) -> NonPaginatedMetricResult:
        """Transform raw summary JSON into a NonPaginatedMetricResult."""
        if not isinstance(raw_json, dict):
            raise MalformedResponseError(f"Expected JSON object, got {type(raw_json).__name__}")

        raw_metrics = raw_json.get("metrics") or raw_json.get("summary") or raw_json.get("data")
        metric_items = []
        if isinstance(raw_metrics, list):
            for m in raw_metrics:
                if isinstance(m, dict):
                    metric_items.append(MetricItem(
                        label=str(m.get("label", m.get("name", "metric"))),
                        value=m.get("value", 0),
                        unit=m.get("unit"),
                    ))
        elif isinstance(raw_metrics, dict):
            for k, v in raw_metrics.items():
                metric_items.append(MetricItem(label=str(k), value=v))

        source = self.build_source(
            endpoint=endpoint,
            report_code=report_id.lower(),
            api_id=f"netiq_{report_id.lower()}",
            mode=mode,
        )

        return NonPaginatedMetricResult(
            reportId=report_id,
            domain=domain,
            status=ReportStatus.SUCCESS,
            metrics=metric_items,
            source=source,
        )


class ResponseAdapterRegistry:
    """Registry providing the appropriate adapter instance for a report definition."""

    @staticmethod
    def get_adapter(report_def: ReportDefinition | dict[str, Any] | None = None) -> BaseResponseAdapter:
        """Select the appropriate response adapter based on report domain or metadata.
        
        Args:
            report_def: Report definition model or dictionary.
            
        Returns:
            BaseResponseAdapter: Configured adapter instance.
        """
        rep_dict = report_def.model_dump() if isinstance(report_def, ReportDefinition) else (report_def or {})
        domain = rep_dict.get("domain", "").upper()
        if domain == "AUDIT":
            return PaginatedAuditResponseAdapter(report_def)
        return PaginatedInventoryResponseAdapter(report_def)
