"""Authentication integration and token management."""

from typing import Any
from src.settings.env import settings


class AuthenticationError(Exception):
    """Raised when authentication credentials are missing or invalid."""
    pass


class AuthManager:
    """Manages authentication headers for outgoing NETIQ backend requests."""

    @staticmethod
    def get_auth_headers(token: str | None = None) -> dict[str, str]:
        """Produce authorization header dictionary."""
        effective_token = token or settings.netiq_api_auth_token
        if not effective_token:
            # In LIVE mode, missing auth token is a critical failure
            if settings.netiq_api_mode.value == "LIVE":
                raise AuthenticationError("LIVE mode requires an authenticated NETIQ_API_AUTH_TOKEN.")
            return {}

        return {"Authorization": f"Bearer {effective_token}"}
