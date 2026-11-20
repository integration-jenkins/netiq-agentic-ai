"""Security tests verifying that unverified contracts are gated from LIVE execution."""

import pytest
from src.adapters.netiq_http.allowed_api import AllowlistPolicy, UnverifiedContractError
from src.adapters.netiq_http.client import NetIQHttpClient
from src.schemas.reports import ReportQuery
from src.settings.env import ApiMode


def test_allowlist_policy_blocks_live_unverified_contracts():
    policy = AllowlistPolicy()
    with pytest.raises(UnverifiedContractError, match="LIVE execution blocked"):
        policy.evaluate(method="POST", path="/api/nodes/reports/4g", mode="LIVE")


@pytest.mark.anyio
async def test_http_client_refuses_live_execution_on_unverified_contract():
    client = NetIQHttpClient(mode=ApiMode.LIVE)
    query = ReportQuery(report_id="RAN_CELL_4G", circle="BR")
    with pytest.raises(UnverifiedContractError, match="LIVE execution"):
        await client.execute_report_query(query)
    await client.close()
