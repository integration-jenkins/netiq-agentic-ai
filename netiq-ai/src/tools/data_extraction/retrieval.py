"""Deterministic report data retrieval service consuming standardized responses.

Architecture Role:
------------------
This service provides deterministic data extraction tools for AI agents and workflows.
Instead of allowing agents or LLMs to construct arbitrary HTTP queries or parse raw JSON,
they interact with this service.

Key Guarantees:
---------------
1. Consumes Normalized Models: Operates exclusively on typed `ReportPage` models.
2. Bounded Pagination: Enforces safety limits (`max_retrieval_pages`, `max_retrieval_records`)
   from `configs/limits.yaml` to prevent runaway memory usage.
3. Infinite Loop Prevention: Detects non-advancing page numbers and zero-record pages
   with `hasNext=True`, terminating safely.
4. Contradiction Rejection: Validates pagination math; rejects any backend response where
   `returnedRecords != len(data)` or negative counts are present.
5. Aggregate Optimization: Prefers backend total count calculations over downloading
   millions of records to count them.
"""

import copy
from typing import Any
from src.adapters.netiq_http.client import NetIQHttpClient
from src.schemas.errors import ErrorCode, StandardError
from src.schemas.reports import ReportPage, ReportPagination, ReportQuery, ReportStatus
from src.settings.loader import load_limits_config


class RetrievalError(Exception):
    """Base exception for data retrieval operations."""
    pass


class ContradictoryPaginationError(RetrievalError):
    """Raised when backend pagination metadata contradicts the returned data array."""
    pass


class PaginationLimitExceededError(RetrievalError):
    """Raised when a query attempts to retrieve data beyond configured safety ceilings."""
    pass


class ReportRetrievalService:
    """Consumes standardized ReportPage responses with deterministic pagination bounds."""

    def __init__(self, http_client: NetIQHttpClient | None = None) -> None:
        """Initialize retrieval service with HTTP client and configured limits.
        
        Args:
            http_client: NetIQ HTTP client instance (defaults to NetIQHttpClient).
        """
        self.http_client = http_client or NetIQHttpClient()
        limits = load_limits_config().get("pagination", {})
        self.default_page_size = int(limits.get("default_page_size", 50))
        self.max_page_size = int(limits.get("max_page_size", 500))
        self.max_retrieval_pages = int(limits.get("max_retrieval_pages", 10))
        self.max_retrieval_records = int(limits.get("max_retrieval_records", 1000))

    async def get_single_page(
        self,
        query: ReportQuery,
        user_permitted_circles: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> ReportPage:
        """Fetch a single standardized page of report data.
        
        Clamps requested page size to `max_page_size` and verifies pagination consistency.
        
        Args:
            query: Normalized query parameters.
            user_permitted_circles: Circles caller is authorized to view.
            correlation_id: Tracking ID for request tracing.
            
        Returns:
            ReportPage: Canonical standardized report page.
            
        Raises:
            ContradictoryPaginationError: If backend pagination fields are contradictory.
        """
        # Clamp page size to configured safety ceiling
        if query.size > self.max_page_size:
            query = query.model_copy(update={"size": self.max_page_size})

        page = await self.http_client.execute_report_query(
            query=query,
            user_permitted_circles=user_permitted_circles,
            correlation_id=correlation_id,
        )
        self._validate_pagination_consistency(page.pagination, len(page.data))
        return page

    async def retrieve_bounded_dataset(
        self,
        query: ReportQuery,
        max_pages: int | None = None,
        max_records: int | None = None,
        user_permitted_circles: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> ReportPage:
        """Retrieve multi-page results up to safe deterministic bounds.
        
        Paginates sequentially while respecting safety ceilings:
        - Stops if `hasNext` becomes False.
        - Stops if `pages_retrieved >= max_pages`.
        - Stops if `total_records >= max_records`.
        - Stops if loop detects duplicate page or zero returned records.
        - Marks `status=PARTIAL` if pagination was truncated by safety limits.
        
        Args:
            query: Initial query specification.
            max_pages: Maximum pages to retrieve (capped by system limit).
            max_records: Maximum total rows to accumulate (capped by system limit).
            user_permitted_circles: User's circle scope.
            correlation_id: Request tracking ID.
            
        Returns:
            ReportPage: Aggregated report page containing accumulated rows.
        """
        effective_max_pages = min(max_pages or self.max_retrieval_pages, self.max_retrieval_pages)
        effective_max_records = min(max_records or self.max_retrieval_records, self.max_retrieval_records)

        current_query = query.model_copy(update={"page": query.page or 0, "size": min(query.size, self.max_page_size)})
        first_page = await self.get_single_page(
            query=current_query,
            user_permitted_circles=user_permitted_circles,
            correlation_id=correlation_id,
        )

        all_rows = list(first_page.data)
        current_page_obj = first_page
        pages_retrieved = 1

        # Track visited page numbers to prevent infinite loops
        seen_pages = {first_page.pagination.page}

        while (
            current_page_obj.pagination.hasNext
            and pages_retrieved < effective_max_pages
            and len(all_rows) < effective_max_records
        ):
            next_page_num = current_page_obj.pagination.page + 1
            if next_page_num in seen_pages:
                # Contradiction: page number did not advance
                break
            seen_pages.add(next_page_num)

            # Prevent requesting further pages if current page returned zero records
            if current_page_obj.pagination.returnedRecords == 0:
                break

            current_query = current_query.model_copy(update={"page": next_page_num})
            next_page = await self.get_single_page(
                query=current_query,
                user_permitted_circles=user_permitted_circles,
                correlation_id=correlation_id,
            )

            if len(next_page.data) == 0:
                break

            all_rows.extend(next_page.data)
            current_page_obj = next_page
            pages_retrieved += 1

        # Check if dataset was truncated by safety bounds
        is_partial = current_page_obj.pagination.hasNext and (
            pages_retrieved >= effective_max_pages or len(all_rows) >= effective_max_records
        )
        if len(all_rows) > effective_max_records:
            all_rows = all_rows[:effective_max_records]

        consolidated_pagination = ReportPagination(
            page=first_page.pagination.page,
            size=len(all_rows) if all_rows else first_page.pagination.size,
            returnedRecords=len(all_rows),
            totalRecords=first_page.pagination.totalRecords,
            hasNext=is_partial or current_page_obj.pagination.hasNext,
        )

        final_status = ReportStatus.PARTIAL if is_partial else first_page.status

        return ReportPage(
            reportId=first_page.reportId,
            domain=first_page.domain,
            status=final_status,
            circle=first_page.circle,
            data=all_rows,
            pagination=consolidated_pagination,
            source=first_page.source,
        )

    def _validate_pagination_consistency(self, p: ReportPagination, actual_count: int) -> None:
        """Reject contradictory backend pagination metadata.
        
        Guarantees that `returnedRecords` strictly equals the actual length of
        the data array, and that page numbers and sizes are positive.
        """
        if p.returnedRecords != actual_count:
            raise ContradictoryPaginationError(
                f"Contradictory pagination: returnedRecords ({p.returnedRecords}) does not match "
                f"actual row count ({actual_count})."
            )
        if p.totalRecords is not None and p.totalRecords < 0:
            raise ContradictoryPaginationError(
                f"Contradictory pagination: totalRecords cannot be negative ({p.totalRecords})."
            )
        if p.page < 0:
            raise ContradictoryPaginationError(f"Contradictory pagination: page cannot be negative ({p.page}).")
        if p.size <= 0:
            raise ContradictoryPaginationError(f"Contradictory pagination: size must be positive ({p.size}).")
