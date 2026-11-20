"""Application port definitions and structural interfaces for NETIQ Agentic AI.

Architecture Role:
------------------
In Hexagonal / Ports-and-Adapters architecture, this module defines the abstract
input/output protocol boundaries ("Ports") decoupling the core business logic from
infrastructure technologies.

Key Interfaces:
---------------
- `ReportDataPort`: Abstract protocol for retrieving standardized report data, implemented
  by `NetIQHttpClient` in `src/adapters/netiq_http/client.py`.
- `AllowlistPolicyPort`: Abstract protocol for validating endpoint safety before HTTP invocation.
- `CircleSecurityPort`: Abstract protocol for validating user circle boundaries.

By coding to these port definitions, domain orchestrators remain 100% testable
and completely independent of specific HTTP libraries or backend implementations.
"""

from typing import Any, Protocol, runtime_checkable
from src.schemas.reports import ReportPage, ReportQuery


@runtime_checkable
class ReportDataPort(Protocol):
    """Abstract port for fetching standardized report pages from an underlying provider."""

    async def execute_report_query(
        self,
        query: ReportQuery,
        user_permitted_circles: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> ReportPage:
        """Execute a report query and return a standardized ReportPage."""
        ...


@runtime_checkable
class AllowlistPolicyPort(Protocol):
    """Abstract port for enforcing API allowlist constraints."""

    def evaluate(self, method: str, path: str, mode: str = "MOCK") -> dict[str, Any]:
        """Evaluate whether an HTTP method and path are authorized."""
        ...


@runtime_checkable
class CircleSecurityPort(Protocol):
    """Abstract port for circle boundary validation."""

    def validate_circle_access(
        self,
        user_permitted_circles: list[str],
        requested_circle: str | None,
        user_roles: list[str] | None = None,
    ) -> str | None:
        """Validate whether the user is permitted to query the requested circle."""
        ...
