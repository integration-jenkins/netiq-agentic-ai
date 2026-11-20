"""Authorization policy enforcement for NETIQ Agentic AI.

Architecture Role:
------------------
This module acts as the internal policy enforcement point (PEP) for agent actions.
It evaluates whether an agent or user is authorized to perform a specific query,
verifies that read-only constraints are respected, and delegates circle boundary checks
to `CircleAccessPolicy`.

Key Guarantees:
---------------
1. Read-Only Protection: Rejects any attempt to execute write or state-changing intents
   against report endpoints.
2. Circle Boundary Verification: Ensures user roles and permitted circle lists are
   strictly evaluated before any backend retrieval is initiated.
"""

from typing import Any
from src.security.circle_access import CircleAccessPolicy, UnauthorizedCircleError


class AuthorizationError(Exception):
    """Raised when an operation violates authorization policies or read-only constraints."""
    pass


class AuthorizationService:
    """Central authorization guard evaluating user identity, roles, and circle boundaries."""

    def __init__(self, circle_policy: CircleAccessPolicy | None = None) -> None:
        """Initialize authorization service with circle access policy."""
        self.circle_policy = circle_policy or CircleAccessPolicy()

    def authorize_report_query(
        self,
        user_permitted_circles: list[str],
        requested_circle: str | None,
        user_roles: list[str] | None = None,
        is_write_intent: bool = False,
    ) -> str | None:
        """Enforce read-only constraint and circle boundaries for a report query.
        
        Args:
            user_permitted_circles: List of circles user has access to.
            requested_circle: Specific circle requested in query.
            user_roles: Security roles assigned to caller.
            is_write_intent: Whether the query attempts to modify data.
            
        Returns:
            str | None: Authorized circle identifier.
            
        Raises:
            AuthorizationError: If query attempts state-changing mutations.
            UnauthorizedCircleError: If user lacks circle access.
        """
        if is_write_intent:
            raise AuthorizationError("State-changing write operations are prohibited on report endpoints.")

        return self.circle_policy.validate_circle_access(
            user_permitted_circles=user_permitted_circles,
            requested_circle=requested_circle,
            user_roles=user_roles,
        )
