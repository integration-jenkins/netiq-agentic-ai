"""Circle-level access enforcement and multi-tenant boundary isolation.

Architecture Role:
------------------
In telecom enterprise operations, data access is partitioned by geographic operating
divisions ("Circles", e.g., DELHI, MUMBAI, PUNJAB, BIHAR). Users are assigned access
to specific circles based on their organizational role.

This module enforces server-side circle isolation:
1. Circle parameters are NEVER trusted directly from user query text.
2. Users cannot query data outside their assigned `user_permitted_circles`.
3. If a circle violation is detected, access is immediately blocked with `UnauthorizedCircleError`.
"""

from typing import Iterable


class UnauthorizedCircleError(Exception):
    """Raised when a user attempts to access telecom data outside their assigned circles."""
    pass


class CircleAccessPolicy:
    """Enforces strict multi-tenant circle isolation for telecom operations."""

    @staticmethod
    def validate_circle_access(
        user_permitted_circles: Iterable[str],
        requested_circle: str | None,
        user_roles: Iterable[str] | None = None,
    ) -> str | None:
        """Verify whether a user is authorized for a requested telecom circle.

        Authorization Rules:
        - Admin or superuser roles bypass single-circle restrictions.
        - Wildcard circle ('*') grants access across all circles.
        - If requested_circle is None:
          - If user has access to exactly 1 circle, auto-defaults to that circle.
          - Otherwise returns None (requires explicit user selection).
        - If requested_circle is specified, it MUST exist in user_permitted_circles (case-insensitive).
        
        Args:
            user_permitted_circles: Circles assigned to user.
            requested_circle: Target circle requested for query.
            user_roles: Security roles assigned to user.
            
        Returns:
            str | None: Normalized uppercase circle code if authorized.
            
        Raises:
            UnauthorizedCircleError: If user lacks permission for the circle.
        """
        roles = {r.lower() for r in (user_roles or [])}
        if "admin" in roles or "superuser" in roles:
            return requested_circle

        permitted = {c.strip().upper() for c in user_permitted_circles if c}
        if "*" in permitted:
            return requested_circle

        if requested_circle is None:
            # If user has access to only 1 circle, default to it deterministically
            if len(permitted) == 1:
                return next(iter(permitted))
            return None

        req_upper = requested_circle.strip().upper()
        if req_upper not in permitted:
            raise UnauthorizedCircleError(
                f"Access denied: User is not authorized to access circle '{requested_circle}'. "
                f"Permitted circles: {sorted(permitted)}"
            )

        return req_upper
