"""Authorization policy enforcement for NETIQ Agentic AI."""

from typing import Any
from src.security.circle_access import CircleAccessPolicy, UnauthorizedCircleError


class AuthorizationError(Exception):
    """Raised when an operation violates authorization policies."""
    pass


class AuthorizationService:
    """Central authorization guard evaluating user identity, roles, and circle boundaries."""

    def __init__(self, circle_policy: CircleAccessPolicy | None = None) -> None:
        self.circle_policy = circle_policy or CircleAccessPolicy()

    def authorize_report_query(
        self,
        user_permitted_circles: list[str],
        requested_circle: str | None,
        user_roles: list[str] | None = None,
        is_write_intent: bool = False,
    ) -> str | None:
        """Enforce read-only constraint and circle boundaries."""
        if is_write_intent:
            raise AuthorizationError("State-changing write operations are prohibited on report endpoints.")

        return self.circle_policy.validate_circle_access(
            user_permitted_circles=user_permitted_circles,
            requested_circle=requested_circle,
            user_roles=user_roles,
        )
