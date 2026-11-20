"""Health-check API routes."""

from src.settings.env import settings


async def health() -> dict:
    return {"status": "ok", "mode": settings.netiq_api_mode.value}
