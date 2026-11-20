"""Circle-level access enforcement and boundary isolation."""

from typing import Iterable


class UnauthorizedCircleError(Exception):
    """Raised when a user attempts to access data outside their assigned circles."""
    pass


class CircleAccessPolicy:
    """Enforces strict multi-tenant circle isolation for telecom operations."""

    @staticmethod
    def validate_circle_access(
        user_permitted_circles: Iterable[str],
        requested_circle: str | None,
        user_roles: Iterable[str] | None = None,
    ) -> str | None:
        """Verify whether user is authorized for the requested circle.

        Rules:
        - Admin or superuser roles may bypass single-circle restriction.
        - If user permitted circles contains '*', all circles are accessible.
        - If requested_circle is None, returns None (or default user circle).
        - If requested_circle is specified, it MUST exist in user_permitted_circles (case-insensitive).
        """
        roles = {r.lower() for r in (user_roles or [])}
        if "admin" in roles or "superuser" in roles:
            return requested_circle

        permitted = {c.strip().upper() for c in user_permitted_circles if c}
        if "*" in permitted:
            return requested_circle

        if requested_circle is None:
            # If user has only 1 circle, default to it; otherwise require explicit selection
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
