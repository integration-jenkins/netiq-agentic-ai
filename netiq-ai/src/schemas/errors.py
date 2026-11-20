"""Standard error schemas and error codes for NETIQ Agentic AI.

Architecture Role:
------------------
This module defines the standardized error hierarchy for the application.
Instead of allowing raw Python traceback strings or opaque HTTP error status codes
to propagate to agents and UI layers, all system exceptions are mapped to these
strongly-typed error models.

Key Guarantees:
---------------
1. Uniform Error Payloads: Every error contains a standardized machine-readable `code`,
   a human-readable `message`, and structured context `details`.
2. Clean Recovery for Agents: Agents can inspect `code` deterministically to decide
   whether to refine queries, alert the user to circle restrictions, or abort safely.
3. Fail-Closed Security: Security violations and unauthorized circle accesses are
   cleanly distinguished from network timeouts and backend unavailability.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(str, Enum):
    """Categorized error codes for deterministic system behavior.
    
    - INVALID_QUERY: Query parameters fail validation (e.g. negative page number or invalid sort).
    - UNAUTHORIZED_CIRCLE: User attempts to access telecom circle data outside their granted scope.
    - UNVERIFIED_CONTRACT: LIVE mode attempted against an unverified Java API contract.
    - SECURITY_VIOLATION: Attempted access to non-whitelisted path, mutation API, or path traversal.
    - BACKEND_TIMEOUT: Network read or connection timeout communicating with backend gateway.
    - BACKEND_UNAVAILABLE: Backend gateway returned HTTP 500, 502, 503, or failed to connect.
    - MALFORMED_RESPONSE: Backend returned non-JSON, invalid JSON, or missing required rows path.
    - CONTRADICTORY_PAGINATION: Backend returned inconsistent counts (e.g. returnedRecords != len(data)).
    - REPORT_NOT_FOUND: Requested report identifier does not exist in version-controlled catalog.
    - PAGINATION_LIMIT_EXCEEDED: Requested retrieval exceeded safe bounded pagination limits.
    - UNSUPPORTED_OPERATION: Requested operation is not supported by current offline or mock runtime.
    """
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
    """Normalized structured error representation.
    
    Emitted whenever an operation in the retrieval service, HTTP client, or
    orchestrator fails. Included in the `errors` array of `ChatResponse`.
    """
    model_config = ConfigDict(frozen=True)

    code: ErrorCode = Field(..., description="Machine-readable standardized error classification")
    message: str = Field(..., description="Descriptive explanation of the error cause")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured debugging context or error parameters")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of error occurrence"
    )
