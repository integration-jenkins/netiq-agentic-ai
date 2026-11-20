"""Asynchronous HTTP client for approved NETIQ Java APIs with MOCK and LIVE support."""

import json
from pathlib import Path
from typing import Any
import uuid
import httpx

from src.adapters.netiq_http.allowed_api import (
    AllowlistPolicy,
    SecurityViolationError,
    UnverifiedContractError,
    default_allowlist_policy,
)
from src.adapters.netiq_http.response_adapters import (
    BaseResponseAdapter,
    MalformedResponseError,
    ResponseAdapterRegistry,
)
from src.schemas.errors import ErrorCode, StandardError
from src.schemas.metadata import ReportDefinition
from src.schemas.reports import ReportMode, ReportPage, ReportQuery
from src.security.authentication import AuthManager
from src.security.circle_access import CircleAccessPolicy, UnauthorizedCircleError
from src.settings.env import ApiMode, settings
from src.settings.loader import load_limits_config, load_report_definition


class NetIQClientError(Exception):
    """Base exception for NetIQ HTTP client."""
    pass


class BackendUnavailableError(NetIQClientError):
    """Raised when the backend API cannot be reached or returns 5xx."""
    pass


class BackendTimeoutError(NetIQClientError):
    """Raised when an API call times out."""
    pass


class NetIQHttpClient:
    """Enterprise client for NETIQ backend integration."""

    def __init__(
        self,
        base_url: str | None = None,
        mode: ApiMode | None = None,
        allowlist_policy: AllowlistPolicy | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.netiq_api_base_url).rstrip("/")
        self.mode = mode or settings.netiq_api_mode
        self.allowlist_policy = allowlist_policy or default_allowlist_policy
        self._limits = load_limits_config()

        # HTTP limits
        http_cfg = self._limits.get("http", {})
        self.connect_timeout = float(http_cfg.get("connect_timeout_seconds", 5.0))
        self.read_timeout = float(http_cfg.get("read_timeout_seconds", 15.0))
        self.max_retries = int(http_cfg.get("max_retries", 2))
        self.max_response_bytes = int(http_cfg.get("max_response_bytes", 5242880))

        # Reusable async client with connection pooling
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.read_timeout, connect=self.connect_timeout),
            transport=transport,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )

    async def close(self) -> None:
        """Close client sessions and connection pool."""
        await self._client.aclose()

    async def __aenter__(self) -> "NetIQHttpClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def _resolve_fixture_path(self, report_code: str, report_id: str) -> Path:
        """Locate appropriate synthetic fixture on disk for MOCK mode."""
        clean_code = (report_code or "").lower().replace("-", "_")
        clean_id = (report_id or "").lower()

        candidate_map = {
            "4g": "ran_cell_4g.json",
            "5g": "ran_cell_5g.json",
            "node_report": "ran_node_inventory.json",
            "ran_node_inventory": "ran_node_inventory.json",
            "mw_node": "mw_node_inventory.json",
            "mw_duplicate_node": "mw_duplicate_nodes.json",
            "ftth_node": "ftth_node_inventory.json",
            "wireline_node": "wireline_node_inventory.json",
            "missing_remarks": "audit_missing_remarks.json",
        }

        filename = candidate_map.get(clean_code) or candidate_map.get(clean_id)
        if filename:
            path = settings.fixtures_dir / filename
            if path.is_file():
                return path

        # Default fallback fixture
        fallback = settings.fixtures_dir / "sample_report_response.json"
        if fallback.is_file():
            return fallback
        return settings.fixtures_dir / "ran_node_inventory.json"

    async def execute_report_query(
        self,
        query: ReportQuery,
        user_permitted_circles: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> ReportPage:
        """Execute a report query through MOCK fixtures or verified LIVE endpoint."""
        corr_id = correlation_id or str(uuid.uuid4())

        # 1. Load report metadata
        report_meta = load_report_definition(query.report_id)
        report_id = report_meta.get("id", query.report_id)
        domain = report_meta.get("domain", "RAN")
        rep_code = report_meta.get("report_code", query.report_id)

        api_meta = report_meta.get("api")
        if not api_meta:
            raise NetIQClientError(
                f"Report '{report_id}' does not have an approved API mapping established in source metadata."
            )

        method = api_meta.get("method", "POST").upper()
        path = api_meta.get("path", "")
        contract_status = api_meta.get("verification_status", "UNVERIFIED")

        # 2. Circle authorization check
        if user_permitted_circles is not None:
            effective_circle = CircleAccessPolicy.validate_circle_access(
                user_permitted_circles=user_permitted_circles,
                requested_circle=query.circle,
            )
        else:
            effective_circle = query.circle

        # 3. Security evaluation against allowlist
        self.allowlist_policy.evaluate(method=method, path=path, mode=self.mode.value)

        # 4. Mode branch
        if self.mode == ApiMode.MOCK:
            # Load local synthetic fixture
            fixture_path = self._resolve_fixture_path(rep_code, report_id)
            if not fixture_path.is_file():
                raise NetIQClientError(f"Fixture file missing for MOCK execution: {fixture_path}")

            try:
                with open(fixture_path, "r", encoding="utf-8") as f:
                    raw_json = json.load(f)
            except Exception as e:
                raise MalformedResponseError(f"Failed to read synthetic fixture at {fixture_path}: {e}") from e

            # Pass through the exact same response normalization adapter as LIVE
            adapter = ResponseAdapterRegistry.get_adapter(report_meta)
            normalized_page = adapter.adapt(
                raw_json=raw_json,
                report_id=report_id,
                domain=domain,
                endpoint=path,
                report_code=rep_code,
                mode=ReportMode.MOCK,
                circle=effective_circle,
                contract_status=contract_status,
                query_page=query.page,
                query_size=query.size,
            )
            return normalized_page

        # LIVE Mode Execution
        # If contract is not verified, fail closed
        if contract_status != "VERIFIED" or not api_meta.get("production_eligible", False):
            raise UnverifiedContractError(
                f"Refusing to execute LIVE query on unverified contract: [{method} {path}]. "
                "Production LIVE execution requires confirmed backend contract verification."
            )

        headers = {
            "X-Correlation-ID": corr_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
            **AuthManager.get_auth_headers(),
        }

        body = {
            "page": query.page,
            "size": query.size,
            "circle": effective_circle,
            "filters": query.filters,
            "columns": query.columns,
            "sortBy": query.sort_by,
            "sortDirection": query.sort_direction,
        }

        # Bounded retry loop for idempotent requests
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if method == "POST":
                    resp = await self._client.post(path, json=body, headers=headers)
                elif method == "GET":
                    params = {"page": query.page, "size": query.size}
                    if effective_circle:
                        params["circle"] = effective_circle
                    resp = await self._client.get(path, params=params, headers=headers)
                else:
                    raise SecurityViolationError(f"Unsupported HTTP method: {method}")

                # Validate response size limit
                if len(resp.content) > self.max_response_bytes:
                    raise NetIQClientError(
                        f"Response payload exceeded max size limit of {self.max_response_bytes} bytes."
                    )

                if resp.status_code >= 500:
                    raise BackendUnavailableError(f"NETIQ backend returned HTTP {resp.status_code}: {resp.text}")
                elif resp.status_code >= 400:
                    raise NetIQClientError(f"NETIQ backend returned HTTP {resp.status_code}: {resp.text}")

                raw_json = resp.json()

                # Normalize response using adapter
                adapter = ResponseAdapterRegistry.get_adapter(report_meta)
                return adapter.adapt(
                    raw_json=raw_json,
                    report_id=report_id,
                    domain=domain,
                    endpoint=path,
                    report_code=rep_code,
                    mode=ReportMode.LIVE,
                    circle=effective_circle,
                    contract_status=contract_status,
                    query_page=query.page,
                    query_size=query.size,
                )

            except httpx.TimeoutException as te:
                last_error = BackendTimeoutError(f"Request timeout connecting to {path}: {te}")
            except httpx.RequestError as re:
                last_error = BackendUnavailableError(f"Network error communicating with NETIQ backend: {re}")

        raise last_error or BackendUnavailableError(f"Failed to execute LIVE request to {path}")
