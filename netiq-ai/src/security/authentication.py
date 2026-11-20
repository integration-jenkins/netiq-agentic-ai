"""Authentication integration and token management for NETIQ backend APIs.

Architecture Role:
------------------
This module manages outbound HTTP authentication credentials when communicating with
the live NETIQ Java Spring Boot backend.

Key Guarantees:
---------------
1. Fail-Closed in LIVE Mode: In LIVE mode, missing or empty authentication tokens
   raise an immediate `AuthenticationError`.
2. Safe in MOCK Mode: In MOCK mode, missing tokens are gracefully bypassed because
   no external network requests are made.
3. Clean Separation: Isolates authentication token management from business schemas
   and response normalization.
"""

from typing import Any
from src.settings.env import settings


class AuthenticationError(Exception):
    """Raised when authentication credentials are missing or invalid."""
    pass


class AuthManager:
    """Manages authentication headers for outgoing NETIQ backend requests."""

    @staticmethod
    def get_auth_headers(token: str | None = None) -> dict[str, str]:
        """Produce authorization header dictionary for HTTP requests.
        
        Args:
            token: Optional explicit token. If None, falls back to `settings.netiq_api_auth_token`.
            
        Returns:
            dict[str, str]: Header dictionary containing Authorization Bearer token.
            
        Raises:
            AuthenticationError: If mode is LIVE and no token is available.
        """
        effective_token = token or settings.netiq_api_auth_token
        if not effective_token:
            # LIVE mode strictly requires an authenticated token
            if settings.netiq_api_mode.value == "LIVE":
                raise AuthenticationError("LIVE mode requires an authenticated NETIQ_API_AUTH_TOKEN.")
            return {}

        return {"Authorization": f"Bearer {effective_token}"}
