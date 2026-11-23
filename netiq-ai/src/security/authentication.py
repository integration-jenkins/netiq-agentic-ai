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
from src.schemas.user import UserContext
from src.settings.env import AppEnvironment, settings


class AuthenticationError(Exception):
    """Raised when authentication credentials are missing or invalid."""
    pass


class AuthManager:
    """Manages authentication headers for outgoing NETIQ backend requests and incoming API auth."""

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

    @staticmethod
    def authenticate_incoming_request(
        authorization: str | None = None,
        api_key: str | None = None,
        enforce: bool | None = None,
    ) -> UserContext:
        """Authenticate incoming API request and return verified UserContext.
        
        Args:
            authorization: Raw Authorization header (e.g. 'Bearer <token>').
            api_key: Optional X-NETIQ-API-KEY header.
            enforce: Whether to enforce token check (defaults to settings.enforce_api_auth or PROD).
            
        Returns:
            UserContext: Authenticated user context.
            
        Raises:
            AuthenticationError: If enforcement is active and credentials are invalid or missing.
        """
        should_enforce = (
            enforce 
            if enforce is not None 
            else (settings.enforce_api_auth or settings.app_env in (AppEnvironment.PRODUCTION, AppEnvironment.STAGING))
        )

        extracted_token = None
        if authorization:
            parts = authorization.strip().split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                extracted_token = parts[1]
            elif len(parts) == 1:
                extracted_token = parts[0]
        elif api_key:
            extracted_token = api_key.strip()

        if should_enforce:
            if not extracted_token:
                raise AuthenticationError("Missing required authentication token in Authorization or X-NETIQ-API-KEY header.")
            if extracted_token != settings.api_auth_token:
                raise AuthenticationError("Invalid or expired authentication credentials.")

        # If token matches admin token or contains admin tag
        is_admin = extracted_token is not None and "admin" in extracted_token.lower()
        roles = ["admin"] if is_admin else ["telecom_analyst"]

        return UserContext(
            username="admin_user" if is_admin else "analyst_user",
            roles=roles,
            permitted_circles=["*"] if is_admin else ["DL", "MH", "PUNJAB", "BIHAR", "BR"],
            is_admin=is_admin,
            token=extracted_token,
        )
