"""Metadata API routes."""

from fastapi import HTTPException


async def list_reports() -> dict:
    # TODO: read from src.settings.loader.load_catalog_config().
    raise HTTPException(status_code=501, detail="Not implemented yet.")


async def get_report(report_id: str) -> dict:
    # TODO: read from src.settings.loader.load_report_definition().
    raise HTTPException(status_code=501, detail="Not implemented yet.")
