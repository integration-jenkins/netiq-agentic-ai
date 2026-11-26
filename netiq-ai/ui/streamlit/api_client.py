"""Centralized HTTPX API client for Streamlit -> FastAPI communication.

Guarantees:
1. Exclusive Backend Access: All data, metadata, health, and exports flow through FastAPI.
2. Safe Retries: Only idempotent GET requests retry on transient transport errors.
3. No Duplicate Expensive Execution: POST requests (/v1/chat, /v1/inference) never auto-retry.
4. Correlation Tracing: Attaches X-Correlation-ID to every request.
"""

from __future__ import annotations

import uuid
from typing import Any
import httpx

from config import UIConfig, get_ui_config


class NetiqApiError(Exception):
    """Standardized API error raised when FastAPI returns an error or is unreachable."""

    def __init__(self, message: str, status_code: int | None = None, correlation_id: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.correlation_id = correlation_id


class NetiqApiClient:
    """HTTPX client with connection pooling and standardized error handling."""

    def __init__(
        self,
        config: UIConfig | None = None,
        api_key_override: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config or get_ui_config()
        self.api_key = api_key_override if api_key_override is not None else self.config.api_key
        self._client = httpx.Client(
            base_url=self.config.api_base_url,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            transport=transport,
        )

    def _headers(self, correlation_id: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "X-Correlation-ID": correlation_id or str(uuid.uuid4()),
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-NETIQ-API-KEY"] = self.api_key
        return headers

    def _handle_response(self, resp: httpx.Response, correlation_id: str) -> Any:
        if resp.status_code >= 400:
            detail = f"HTTP {resp.status_code}"
            try:
                body = resp.json()
                if isinstance(body, dict) and body.get("detail"):
                    detail = str(body["detail"])
            except Exception:
                pass
            raise NetiqApiError(detail, status_code=resp.status_code, correlation_id=correlation_id)

        try:
            return resp.json()
        except Exception as err:
            raise NetiqApiError(f"Invalid JSON response from backend: {err}", correlation_id=correlation_id) from err

    def _get(self, path: str, params: dict[str, Any] | None = None, timeout: float | None = None) -> Any:
        """Execute idempotent GET with 1 safe retry on transient connection error."""
        cid = str(uuid.uuid4())
        req_timeout = timeout or self.config.metadata_timeout
        last_err: Exception | None = None
        for attempt in range(2):
            try:
                resp = self._client.get(path, params=params, headers=self._headers(cid), timeout=req_timeout)
                return self._handle_response(resp, cid)
            except (httpx.ConnectError, httpx.ReadTimeout) as err:
                last_err = err
                if attempt == 0:
                    continue
        raise NetiqApiError(
            f"Backend unavailable at {self.config.api_base_url}: {last_err}",
            status_code=503,
            correlation_id=cid,
        )

    def _post(self, path: str, payload: dict[str, Any], timeout: float | None = None) -> Any:
        """Execute non-idempotent POST without automatic retries."""
        cid = str(uuid.uuid4())
        req_timeout = timeout or self.config.request_timeout
        try:
            resp = self._client.post(path, json=payload, headers=self._headers(cid), timeout=req_timeout)
            return self._handle_response(resp, cid)
        except httpx.TimeoutException as err:
            raise NetiqApiError(f"Request timed out after {req_timeout}s.", status_code=504, correlation_id=cid) from err
        except httpx.RequestError as err:
            raise NetiqApiError(
                f"Cannot reach FastAPI backend at {self.config.api_base_url}: {err}",
                status_code=503,
                correlation_id=cid,
            ) from err

    def get_health(self, details: bool = False) -> dict[str, Any]:
        return self._get("/health", params={"details": "true"} if details else None)

    def get_circles(self) -> list[str]:
        data = self._get("/v1/metadata/circles")
        return data.get("circles", [])

    def get_domains(self) -> list[str]:
        data = self._get("/v1/metadata/domains")
        return data.get("domains", [])

    def get_reports(self, domain: str | None = None) -> list[dict[str, Any]]:
        params = {"domain": domain} if domain else None
        data = self._get("/v1/metadata/reports", params=params)
        return data.get("reports", [])

    def get_agents(self) -> list[dict[str, Any]]:
        data = self._get("/v1/metadata/agents")
        return data.get("agents", [])

    def send_chat(
        self,
        session_id: str,
        question: str,
        circle: str | None = None,
        domain: str | None = None,
        report_id: str | None = None,
        page: int = 0,
        size: int = 50,
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if circle:
            filters["circle"] = circle
        if domain:
            filters["domain"] = domain
        if report_id:
            filters["report_id"] = report_id

        payload = {
            "sessionId": session_id,
            "question": question,
            "filters": filters,
            "pagination": {"page": page, "size": size},
        }
        return self._post("/v1/chat", payload)

    def get_result_page(
        self,
        result_id: str,
        page: int = 0,
        size: int = 50,
        search: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "size": size}
        if search:
            params["search"] = search
        return self._get(f"/v1/results/{result_id}", params=params, timeout=self.config.request_timeout)

    def generate_export(self, result_id: str) -> dict[str, Any]:
        return self._post("/v1/export", {"resultId": result_id, "format": "XLSX"})

    def download_export_bytes(self, file_id: str) -> bytes:
        cid = str(uuid.uuid4())
        try:
            resp = self._client.get(
                f"/v1/export/{file_id}",
                headers=self._headers(cid),
                timeout=self.config.request_timeout,
            )
            if resp.status_code >= 400:
                raise NetiqApiError(f"Download failed with HTTP {resp.status_code}", status_code=resp.status_code, correlation_id=cid)
            return resp.content
        except httpx.RequestError as err:
            raise NetiqApiError(f"Failed to download export: {err}", status_code=503, correlation_id=cid) from err

    def test_agent(self, agent: str, question: str, circle: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"agent": agent, "question": question}
        if circle:
            payload["circle"] = circle
        return self._post("/v1/agents/test", payload)

    def run_inference(self, prompt: str, role: str | None = None, model: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"prompt": prompt}
        if role:
            payload["role"] = role
        if model:
            payload["model"] = model
        return self._post("/v1/inference", payload)
