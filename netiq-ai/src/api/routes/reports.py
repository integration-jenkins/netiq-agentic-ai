"""Report API routes."""

from fastapi import HTTPException

from src.schemas.reports import ReportPage, ReportQuery


async def query_report(query: ReportQuery) -> ReportPage:
    # TODO: call ReportRetrievalService (src/tools/data_extraction/retrieval.py).
    raise HTTPException(status_code=501, detail="Not implemented yet.")
