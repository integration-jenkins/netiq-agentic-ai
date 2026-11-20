"""Standard error schemas and error codes for NETIQ Agentic AI."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(str, Enum):
    INVALID_QUERY = "INVALID_QUERY"
    UNAUTHORIZED_CIRCLE = "UNAUTHORIZED_CIRCLE"
    UNVERIFIED_CONTRACT = "UNVERIFIED_CONTRACT"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    BACKEND_TIMEOUT = "BACKEND_TIMEOUT"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    CONTRADICTORY_PAGINATION = "CONTRADICTORY_PAGINATION"
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    PAGINATION_LIMIT_EXCEEDED = "PAGINATION_LIMIT_EXCEEDED"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"


class StandardError(BaseModel):
    """Normalized structured error representation."""
    model_config = ConfigDict(frozen=True)

    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
