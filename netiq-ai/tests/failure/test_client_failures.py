"""Failure tests simulating network timeouts, backend 500 errors, and malformed contracts."""

import httpx
import pytest
from src.adapters.netiq_http.client import (
    BackendTimeoutError,
    BackendUnavailableError,
    NetIQHttpClient,
)
from src.schemas.reports import ReportPagination, ReportQuery
from src.settings.env import ApiMode
from src.settings.loader import ConfigurationError
from src.tools.data_extraction.retrieval import (
    ContradictoryPaginationError,
    ReportRetrievalService,
)


def mock_verified_report_definition(report_id: str):
    return {
        "id": report_id,
        "domain": "RAN",
        "report_code": "4g",
        "api": {
            "method": "POST",
            "path": "/api/nodes/reports/4g",
            "verification_status": "VERIFIED",
            "production_eligible": True,
        },
        "response_mapping": {"rows_path": "data"},
    }


@pytest.mark.anyio
async def test_backend_500_raises_unavailable_error(monkeypatch):
    import src.adapters.netiq_http.client as client_mod
    monkeypatch.setattr(client_mod, "load_report_definition", mock_verified_report_definition)

    # Simulate backend 500 with MockTransport
    transport = httpx.MockTransport(
        lambda req: httpx.Response(500, json={"message": "Internal Server Error"})
    )
    # Using LIVE mode with mock transport to verify network failure handling
    client = NetIQHttpClient(mode=ApiMode.LIVE, transport=transport)

    client.allowlist_policy.evaluate = lambda method, path, mode: {
        "id": "test_api",
        "method": "POST",
        "path_template": path,
        "read_only": True,
        "contract_status": "VERIFIED",
        "production_eligible": True,
    }

    query = ReportQuery(report_id="RAN_CELL_4G", circle="BR")
    with pytest.raises(BackendUnavailableError, match="HTTP 500"):
        await client.execute_report_query(query)
    await client.close()


@pytest.mark.anyio
async def test_backend_timeout_raises_timeout_error(monkeypatch):
    import src.adapters.netiq_http.client as client_mod
    monkeypatch.setattr(client_mod, "load_report_definition", mock_verified_report_definition)

    def timeout_handler(req):
        raise httpx.ReadTimeout("Socket read timed out")

    transport = httpx.MockTransport(timeout_handler)
    client = NetIQHttpClient(mode=ApiMode.LIVE, transport=transport)
    client.allowlist_policy.evaluate = lambda method, path, mode: {
        "id": "test_api",
        "method": "POST",
        "path_template": path,
        "read_only": True,
        "contract_status": "VERIFIED",
        "production_eligible": True,
    }

    query = ReportQuery(report_id="RAN_CELL_4G", circle="BR")
    with pytest.raises(BackendTimeoutError, match="timeout"):
        await client.execute_report_query(query)
    await client.close()


def test_contradictory_pagination_validation():
    service = ReportRetrievalService()
    p = ReportPagination(page=0, size=50, returnedRecords=10, totalRecords=100, hasNext=False)
    with pytest.raises(ContradictoryPaginationError, match="returnedRecords"):
        service._validate_pagination_consistency(p, actual_count=5)  # 10 != 5


@pytest.mark.anyio
async def test_nonexistent_report_id_raises_configuration_error():
    client = NetIQHttpClient(mode=ApiMode.MOCK)
    query = ReportQuery(report_id="NON_EXISTENT_REPORT_XYZ")
    with pytest.raises(ConfigurationError, match="not found in catalog"):
        await client.execute_report_query(query)
    await client.close()
