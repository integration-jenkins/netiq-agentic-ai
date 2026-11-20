"""Deterministic report data retrieval service consuming standardized responses."""

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
    """Raised when pagination fields contradict each other."""
    pass


class PaginationLimitExceededError(RetrievalError):
    """Raised when query exceeds configured retrieval ceilings."""
    pass


class ReportRetrievalService:
    """Consumes standardized ReportPage responses with deterministic pagination bounds."""

    def __init__(self, http_client: NetIQHttpClient | None = None) -> None:
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
        """Fetch a single standardized page of report data."""
        # Sanity check page size against limits
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
        """Retrieve multi-page results up to safe deterministic bounds."""
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

        # Infinite loop prevention and bounded pagination
        seen_pages = {first_page.pagination.page}

        while (
            current_page_obj.pagination.hasNext
            and pages_retrieved < effective_max_pages
            and len(all_rows) < effective_max_records
        ):
            next_page_num = current_page_obj.pagination.page + 1
            if next_page_num in seen_pages:
                # Contradiction: page not advancing
                break
            seen_pages.add(next_page_num)

            # Prevent requesting further pages if current returned zero records
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

        # If records exceed bound, trim to ceiling
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
        """Reject contradictory backend pagination metadata."""
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
