"""Chat request and response schemas for the NETIQ Agentic AI user interface.

Architecture Role:
------------------
This module defines the external contract for conversation requests and responses.
All user queries submitted via REST APIs, Streamlit UI, or orchestration graph
must pass through `ChatRequest`, and all final answers returned to callers must conform
strictly to `ChatResponse`.

Key Guarantees:
---------------
1. Structured Data Alongside Text: Tabular data is returned in `structured_data`
   allowing the UI to render interactive tables rather than relying on LLM markdown parsing.
2. Mandatory Provenance: Contains `mode` ('MOCK' vs 'LIVE'), `source_api`, and `evidence`
   to ensure the UI can display synthetic data warning banners when running offline.
3. Explicit Failure Reporting: If an error occurs, `status` is marked 'ERROR' and details
   are provided in the `errors` array.
"""

import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from src.schemas.errors import StandardError
from src.schemas.evidence import EvidenceItem
from src.schemas.reports import ReportPagination


class ChatRequest(BaseModel):
    """User conversation request payload.
    
    Captures user query intent, explicit circle context, and security principals
    (user ID, assigned roles, and permitted telecom circles).
    """
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request tracing ID")
    query: str = Field(..., description="Natural language prompt or command submitted by user")
    circle: str | None = Field(default=None, description="Explicit telecom circle filter requested by user")
    user_id: str = Field(default="anonymous_user", description="Authenticated user principal identifier")
    user_roles: list[str] = Field(default_factory=lambda: ["viewer"], description="Security roles assigned to user")
    user_permitted_circles: list[str] = Field(
        default_factory=list,
        description="Authorized circle boundaries assigned to this user (e.g., ['DELHI', 'MUMBAI'])"
    )


class ChatResponse(BaseModel):
    """Production-standardized chat response payload returned to frontend clients.
    
    Guarantees that agents provide deterministic answers, verified counts, structured
    telecom rows, and audit provenance.
    """
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(..., description="Correlating request tracking identifier")
    status: str = Field(default="SUCCESS", description="Execution outcome: 'SUCCESS', 'EMPTY', 'ERROR', or 'PARTIAL'")
    answer: str = Field(..., description="Deterministic natural language answer composed by orchestrator")
    structured_data: list[dict[str, Any]] | None = Field(
        default=None,
        description="Structured tabular records for UI table rendering"
    )
    report_id: str | None = Field(default=None, description="Target report identifier if query resolved to a report")
    applied_filters: dict[str, Any] = Field(default_factory=dict, description="Normalized filters applied during retrieval")
    source_api: str | None = Field(default=None, description="Backend API path or endpoint template utilized")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Traceable evidence items supporting the answer")
    data_version: str | None = Field(default=None, description="Backend snapshot version identifier if provided")
    data_freshness: str | None = Field(default=None, description="Backend data freshness timestamp if provided")
    mode: str = Field(default="MOCK", description="Execution mode provenance: 'MOCK' or 'LIVE'")
    pagination: ReportPagination | None = Field(default=None, description="Pagination metadata if result is paginated")
    limitations: list[str] = Field(default_factory=list, description="Operational disclosures, synthetic warnings, or limits reached")
    errors: list[StandardError] = Field(default_factory=list, description="List of structured errors if execution failed")
