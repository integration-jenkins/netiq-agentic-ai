r"""Exact HTTP method and path-template allowlist enforcement for NETIQ Agentic AI.

Architecture Role:
------------------
This module acts as the API perimeter firewall. It prevents AI agents, tools, or
orchestrator nodes from calling arbitrary, unsafe, or unverified backend endpoints.

Key Guarantees:
---------------
1. Zero Wildcard Authorization: Wildcards like `/api/**` are strictly prohibited.
2. Exact Path-Template Matching: Path templates such as `/api/nodes/reports/{reportType}`
   are compiled into strict regular expressions where the route parameter only permits
   alphanumeric characters, hyphens, and underscores (`^[a-zA-Z0-9_\-]+$`).
3. Anti-Traversal & Sanitization: Rejects path traversal (`..`), backslashes, embedded
   query strings (`?`), or URL fragments (`#`).
4. Mutation Exclusion: Blocks SQL consoles (`DbConsoleController`), ETL imports,
   cache evictions, model training endpoints, and bulk exports.
5. Fail-Closed LIVE Gate: Gated behind `contract_status == 'VERIFIED'` and
   `production_eligible == True`. In Stage 1, LIVE mode execution is strictly blocked.
"""

import re
from typing import Any
from src.settings.loader import load_allowed_apis_config


class SecurityViolationError(Exception):
    """Raised when an unapproved endpoint, HTTP method, or unsafe path is attempted."""
    pass


class UnverifiedContractError(Exception):
    """Raised when an unverified contract is called in LIVE mode."""
    pass


class AllowlistPolicy:
    """Evaluates candidate HTTP requests against the approved API allowlist.
    
    Loads configuration from `configs/allowed_apis.yaml` and compiles exact path
    templates into regex matchers.
    """

    def __init__(self, config: list[dict[str, Any]] | None = None) -> None:
        """Initialize the allowlist policy.
        
        Args:
            config: Optional list of allowlist dictionaries. If None, loads from
                    `configs/allowed_apis.yaml`.
        """
        self._allowed_apis = config if config is not None else load_allowed_apis_config()
        self._compiled_templates = []
        
        # Precompile exact path templates
        for api in self._allowed_apis:
            method = api["method"].upper()
            template = api["path_template"]
            
            # Convert template parameters e.g. {reportType} into strict regex:
            # Matches only alphanumeric, hyphens, and underscores. No slashes or dots.
            regex_str = "^" + re.sub(r"\{[a-zA-Z0-9_]+\}", r"[a-zA-Z0-9_\-]+", template) + "$"
            compiled = re.compile(regex_str)
            self._compiled_templates.append((method, template, compiled, api))

    def evaluate(self, method: str, path: str, mode: str = "MOCK") -> dict[str, Any]:
        """Evaluate a candidate request against the allowlist.
        
        Args:
            method: HTTP method (e.g., 'GET', 'POST').
            path: Exact URL path to invoke (e.g., '/api/nodes/reports/4g').
            mode: Execution mode ('MOCK' or 'LIVE').
            
        Returns:
            dict: The matching allowed API specification dictionary.
            
        Raises:
            SecurityViolationError: If endpoint is unapproved, method is unsupported,
                                   path is unsafe, or endpoint is not read-only.
            UnverifiedContractError: If mode is LIVE but the API contract is unverified.
        """
        norm_method = (method or "").strip().upper()
        norm_path = (path or "").strip()

        # Perimeter Check 1: Reject path traversal, query injections, and fragments
        if ".." in norm_path or "\\" in norm_path or "?" in norm_path or "#" in norm_path:
            raise SecurityViolationError(f"Malformed or unsafe path detected: '{norm_path}'")

        # Perimeter Check 2: Match method and compiled path template
        matched_spec = None
        for tm_method, tm_path, tm_regex, api_spec in self._compiled_templates:
            if tm_method == norm_method and tm_regex.match(norm_path):
                matched_spec = api_spec
                break

        if not matched_spec:
            raise SecurityViolationError(
                f"Access denied: Endpoint [{norm_method} {norm_path}] is not in the approved NETIQ allowlist."
            )

        # Perimeter Check 3: Enforce read-only constraint
        if not matched_spec.get("read_only", False):
            raise SecurityViolationError(
                f"Access denied: Endpoint [{norm_method} {norm_path}] is not classified as read-only."
            )

        # Perimeter Check 4: Stage 1 LIVE Security Gate
        # LIVE calls are blocked if the contract is UNVERIFIED or production_eligible is False
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
        """Convenience method checking whether a request is permitted without raising exceptions.
        
        Returns:
            bool: True if allowed; False otherwise.
        """
        try:
            self.evaluate(method, path, mode)
            return True
        except (SecurityViolationError, UnverifiedContractError):
            return False


# Default singleton allowlist policy instance
default_allowlist_policy = AllowlistPolicy()
