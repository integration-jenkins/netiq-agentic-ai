"""Chat request and response schemas."""

import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from src.schemas.errors import StandardError
from src.schemas.evidence import EvidenceItem
from src.schemas.reports import ReportPagination


class ChatRequest(BaseModel):
    """User conversation request."""
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = Field(..., description="User query or command")
    circle: str | None = Field(default=None, description="Explicit circle context")
    user_id: str = Field(default="anonymous_user")
    user_roles: list[str] = Field(default_factory=lambda: ["viewer"])
    user_permitted_circles: list[str] = Field(default_factory=list, description="List of circles user has access to")


class ChatResponse(BaseModel):
    """Production-standardized chat response payload."""
    model_config = ConfigDict(frozen=True)

    request_id: str
    status: str = "SUCCESS"  # SUCCESS, EMPTY, ERROR, PARTIAL
    answer: str
    structured_data: list[dict[str, Any]] | None = None
    report_id: str | None = None
    applied_filters: dict[str, Any] = Field(default_factory=dict)
    source_api: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    data_version: str | None = None
    data_freshness: str | None = None
    mode: str = "MOCK"  # MOCK or LIVE
    pagination: ReportPagination | None = None
    limitations: list[str] = Field(default_factory=list)
    errors: list[StandardError] = Field(default_factory=list)
