"""Export API routes."""

from fastapi import HTTPException


async def export_report() -> dict:
    # TODO: call src/tools/export once it exists.
    raise HTTPException(status_code=501, detail="Not implemented yet.")
