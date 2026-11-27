"""Report query and paginated verified-result retrieval API routes."""

from fastapi import Header, HTTPException, Query

from src.schemas.reports import ReportPage, ReportPagination, ReportQuery
from src.security.authentication import AuthManager, AuthenticationError
from src.session.identity import session_user_context
from src.security.authorization import AuthorizationError, AuthorizationService
from src.security.circle_access import UnauthorizedCircleError
from src.session.result_store import (
    ResultAccessDeniedError,
    ResultNotFoundError,
    default_result_store,
)
from src.settings.loader import ConfigurationError
from src.tools.data_extraction.retrieval import ReportRetrievalService

_retrieval_service = ReportRetrievalService()
_auth_service = AuthorizationService()


async def get_paginated_result(
    result_id: str,
    page: int = Query(default=0, ge=0, description="Zero-based page index"),
    size: int = Query(default=50, ge=1, le=500, description="Rows per page"),
    search: str | None = Query(default=None, max_length=200, description="Optional substring filter"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
) -> dict:
    """Retrieve one page of an existing verified result without re-running backend queries."""
    try:
        # NETIQ login (Streamlit chat) first: the chat's results belong to that user.
        user = session_user_context(x_session_id) or AuthManager.authenticate_incoming_request(
            authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    try:
        result = default_result_store.get_result(
            result_id=result_id,
            username=user.username,
            is_admin=user.is_admin,
            permitted_circles=user.permitted_circles,
        )
    except ResultNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ResultAccessDeniedError as err:
        raise HTTPException(status_code=403, detail=str(err))

    rows = result.rows
    if search and search.strip():
        needle = search.strip().lower()
        rows = [
            row for row in rows
            if any(needle in str(val).lower() for val in row.values() if val is not None)
        ]

    total = len(rows)
    start = page * size
    end = start + size
    page_rows = rows[start:end]

    pagination = ReportPagination(
        page=page,
        size=size,
        returnedRecords=len(page_rows),
        totalRecords=total,
        hasNext=end < total,
    )

    return {
        "resultId": result.result_id,
        "reportId": result.report_id,
        "reportName": result.report_name,
        "circle": result.circle,
        "domain": result.domain,
        "dataVersion": result.data_version,
        "dataAsOf": result.data_as_of,
        "mode": result.mode,
        "appliedFilters": result.applied_filters,
        "columns": [c.model_dump() for c in result.columns],
        "rows": page_rows,
        "pagination": pagination.model_dump(),
    }


async def query_report(
    query: ReportQuery,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> ReportPage:
    """Execute a standardized ReportQuery through the retrieval service."""
    try:
        user = AuthManager.authenticate_incoming_request(authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    try:
        authorized_circle = _auth_service.authorize_report_query(
            user_permitted_circles=user.permitted_circles,
            requested_circle=query.circle,
            user_roles=user.roles,
        )
    except UnauthorizedCircleError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except AuthorizationError as err:
        raise HTTPException(status_code=403, detail=str(err))

    safe_query = query.model_copy(update={"circle": authorized_circle})
    try:
        return await _retrieval_service.get_single_page(
            query=safe_query,
            user_permitted_circles=user.permitted_circles,
        )
    except ConfigurationError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Report query failed: {err}")
