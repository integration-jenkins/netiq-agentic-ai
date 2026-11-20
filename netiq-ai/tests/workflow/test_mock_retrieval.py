"""Workflow tests verifying end-to-end MOCK retrieval, pagination bounds, and chat composition."""

import pytest
from app.orchestrator.compose import ChatComposer
from app.orchestrator.verify import ResponseVerifier, VerificationError
from src.adapters.netiq_http.client import NetIQHttpClient
from src.schemas.chat import ChatRequest
from src.schemas.reports import ReportMode, ReportQuery, ReportStatus
from src.settings.env import ApiMode
from src.tools.data_extraction.retrieval import ReportRetrievalService


@pytest.mark.anyio
async def test_mock_single_page_retrieval():
    client = NetIQHttpClient(mode=ApiMode.MOCK)
    service = ReportRetrievalService(http_client=client)

    query = ReportQuery(report_id="RAN_CELL_4G", circle="BR", page=0, size=50)
    page = await service.get_single_page(query=query, user_permitted_circles=["BR"])

    assert page.reportId == "RAN_CELL_4G"
    assert page.domain == "RAN"
    assert page.status == ReportStatus.SUCCESS
    assert page.source.mode == ReportMode.MOCK
    assert len(page.data) == 2
    assert page.pagination.returnedRecords == 2
    assert page.pagination.totalRecords == 1500
    assert page.pagination.hasNext is True

    await client.close()


@pytest.mark.anyio
async def test_mock_bounded_retrieval_limits():
    client = NetIQHttpClient(mode=ApiMode.MOCK)
    service = ReportRetrievalService(http_client=client)

    query = ReportQuery(report_id="RAN_CELL_4G", circle="BR", page=0, size=2)
    # Bounded retrieval with max_pages=1
    page = await service.retrieve_bounded_dataset(
        query=query,
        max_pages=1,
        max_records=10,
        user_permitted_circles=["BR"],
    )

    assert page.pagination.returnedRecords == 2
    assert page.source.mode == ReportMode.MOCK
    assert page.status == ReportStatus.PARTIAL

    await client.close()


@pytest.mark.anyio
async def test_chat_response_composition():
    client = NetIQHttpClient(mode=ApiMode.MOCK)
    service = ReportRetrievalService(http_client=client)

    query = ReportQuery(report_id="RAN_NODE_INVENTORY", circle="DELHI", page=0, size=50)
    page = await service.get_single_page(query=query, user_permitted_circles=["DELHI"])

    req = ChatRequest(query="Show RAN nodes in Delhi", circle="DELHI", user_permitted_circles=["DELHI"])
    response = ChatComposer.compose_report_response(
        request=req,
        page=page,
        report_name="RAN Node Inventory",
    )

    assert response.status == "SUCCESS"
    assert response.mode == "MOCK"
    assert "[MOCK DATA]" in response.answer
    assert "Live NETIQ Java API contract is unverified" in response.answer
    assert len(response.evidence) == 1
    assert response.evidence[0].endpoint == "/api/nodes/reports/node-report"
    assert response.evidence[0].mode == "MOCK"
    assert len(response.structured_data) == 2

    await client.close()


def test_provenance_honesty_rejects_mock_claiming_live():
    with pytest.raises(VerificationError, match="Integrity violation"):
        ResponseVerifier.verify_provenance_honesty(
            answer="Here is the verified live production data from NETIQ.",
            mode="MOCK",
        )
