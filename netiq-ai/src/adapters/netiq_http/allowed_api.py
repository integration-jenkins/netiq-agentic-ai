"""Exact HTTP method and path-template allowlist enforcement.

Enforces strict, fail-closed access controls for NETIQ backend APIs:
- No wildcard `/api/**` access permitted.
- Exact path-template matching with strict parameter character validation.
- Rejects state-changing or mutation operations.
- Gates LIVE access behind contract verification and production eligibility.
"""

import re
from typing import Any
from src.settings.loader import load_allowed_apis_config


class SecurityViolationError(Exception):
    """Raised when an unapproved endpoint or HTTP method is attempted."""
    pass


class UnverifiedContractError(Exception):
    """Raised when an unverified contract is called in LIVE mode."""
    pass


class AllowlistPolicy:
    """Evaluates requested HTTP operations against version-controlled allowlist."""

    def __init__(self, config: list[dict[str, Any]] | None = None) -> None:
        self._allowed_apis = config if config is not None else load_allowed_apis_config()
        self._compiled_templates = []
        for api in self._allowed_apis:
            method = api["method"].upper()
            template = api["path_template"]
            # Convert template {param} to strict regex matching [a-zA-Z0-9_\-]+ only
            # No slashes, no dots, no URL encoded traversal
            regex_str = "^" + re.sub(r"\{[a-zA-Z0-9_]+\}", r"[a-zA-Z0-9_\-]+", template) + "$"
            compiled = re.compile(regex_str)
            self._compiled_templates.append((method, template, compiled, api))

    def evaluate(self, method: str, path: str, mode: str = "MOCK") -> dict[str, Any]:
        """Evaluate request against allowlist. Returns matching API spec or raises."""
        norm_method = (method or "").strip().upper()
        norm_path = (path or "").strip()

        # Reject path traversal and suspicious characters
        if ".." in norm_path or "\\" in norm_path or "?" in norm_path or "#" in norm_path:
            raise SecurityViolationError(f"Malformed or unsafe path detected: '{norm_path}'")

        matched_spec = None
        for tm_method, tm_path, tm_regex, api_spec in self._compiled_templates:
            if tm_method == norm_method and tm_regex.match(norm_path):
                matched_spec = api_spec
                break

        if not matched_spec:
            raise SecurityViolationError(
                f"Access denied: Endpoint [{norm_method} {norm_path}] is not in the approved NETIQ allowlist."
            )

        if not matched_spec.get("read_only", False):
            raise SecurityViolationError(
                f"Access denied: Endpoint [{norm_method} {norm_path}] is not classified as read-only."
            )

        # In LIVE mode, enforce contract verification and production eligibility
        if mode.upper() == "LIVE":
            contract_status = matched_spec.get("contract_status", "UNVERIFIED")
            prod_eligible = matched_spec.get("production_eligible", False)
            if contract_status != "VERIFIED" or not prod_eligible:
                raise UnverifiedContractError(
                    f"LIVE execution blocked: Endpoint [{norm_method} {norm_path}] has contract status "
                    f"'{contract_status}' and production_eligible={prod_eligible}. "
                    f"Live Java API contracts must be verified by backend evidence before LIVE mode activation."
                )

        return matched_spec

    def is_allowed(self, method: str, path: str, mode: str = "MOCK") -> bool:
        """Boolean check without raising."""
        try:
            self.evaluate(method, path, mode)
            return True
        except (SecurityViolationError, UnverifiedContractError):
            return False


# Default singleton instance
default_allowlist_policy = AllowlistPolicy()
