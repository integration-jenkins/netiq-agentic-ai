"""Integration tests for /v1/chat, /v1/results, /v1/export, /v1/metadata, and /v1/agents/test."""

import io
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from src.api.app import create_app
from src.session.result_store import default_result_store
from src.tools.export.excel import sanitize_excel_cell

client = TestClient(create_app())


def test_metadata_endpoints_return_catalog_data():
    r_circles = client.get("/v1/metadata/circles")
    assert r_circles.status_code == 200
    assert len(r_circles.json()["circles"]) > 0

    r_domains = client.get("/v1/metadata/domains")
    assert r_domains.status_code == 200
    assert "RAN" in r_domains.json()["domains"]

    r_reports = client.get("/v1/metadata/reports", params={"domain": "RAN"})
    assert r_reports.status_code == 200
    assert r_reports.json()["total_reports"] > 0

    r_agents = client.get("/v1/metadata/agents")
    assert r_agents.status_code == 200
    assert len(r_agents.json()["agents"]) == 6


def test_chat_report_pagination_and_excel_export_flow():
    # 1. Submit chat query
    resp = client.post(
        "/v1/chat",
        json={
            "sessionId": "test-sess-flow-1",
            "question": "Show 4G cell inventory for Bihar",
            "filters": {"circle": "BR"},
            "pagination": {"page": 0, "size": 50},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["intent"] == "REPORT"
    assert data["report_id"] == "RAN_CELL_4G"
    assert data["result_id"] is not None
    assert len(data["metrics"]) >= 2
    assert data["table"] is not None
    assert len(data["table"]["columns"]) > 0
    assert len(data["sources"]) == 1
    assert data["sources"][0]["mode"] == "MOCK"
    assert data["export"]["available"] is True

    result_id = data["result_id"]

    # 2. Fetch paginated result via /v1/results/{result_id}
    r_page = client.get(f"/v1/results/{result_id}", params={"page": 0, "size": 1})
    assert r_page.status_code == 200
    page_data = r_page.json()
    assert page_data["pagination"]["returnedRecords"] <= 1

    # 3. Generate Excel via POST /v1/export
    r_exp = client.post("/v1/export", json={"resultId": result_id, "format": "XLSX"})
    assert r_exp.status_code == 200
    exp_meta = r_exp.json()
    assert exp_meta["status"] == "COMPLETED"
    file_id = exp_meta["fileId"]

    # 4. Download Excel via GET /v1/export/{file_id}
    r_dl = client.get(f"/v1/export/{file_id}")
    assert r_dl.status_code == 200
    assert "spreadsheetml.sheet" in r_dl.headers["content-type"]

    # Verify workbook contains Data and Metadata sheets
    wb = load_workbook(io.BytesIO(r_dl.content))
    assert "Data" in wb.sheetnames
    assert "Metadata" in wb.sheetnames


def test_chat_knowledge_cplane_uplane():
    resp = client.post(
        "/v1/chat",
        json={
            "sessionId": "test-sess-know-1",
            "question": "Explain the difference between CPLANE and UPLANE",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["intent"] == "KNOWLEDGE"
    assert "CPLANE" in data["answer"] and "UPLANE" in data["answer"]
    assert data["table"] is None
    assert len(data["sources"]) >= 1


def test_chat_comparison_two_circles():
    resp = client.post(
        "/v1/chat",
        json={
            "sessionId": "test-sess-cmp-1",
            "question": "Compare RAN inventory between Delhi and Haryana",
            "user_permitted_circles": ["DL", "HR"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "COMPARISON"
    assert len(data["sources"]) == 2
    circles = {s["circle"] for s in data["sources"]}
    assert circles == {"DL", "HR"}


def test_chat_followup_and_export_intent():
    sess = "test-sess-followup-1"
    r1 = client.post(
        "/v1/chat",
        json={
            "sessionId": sess,
            "question": "Show 4G cell inventory for Bihar",
            "filters": {"circle": "BR"},
        },
    )
    assert r1.status_code == 200
    res_id_1 = r1.json()["result_id"]

    # Follow-up export
    r2 = client.post(
        "/v1/chat",
        json={"sessionId": sess, "question": "Export the result"},
    )
    assert r2.status_code == 200
    assert r2.json()["intent"] == "EXPORT"
    assert r2.json()["export"]["resultId"] == res_id_1


def test_unauthorized_circle_and_cross_user_result_rejected():
    # Unauthorized circle
    r_unauth = client.post(
        "/v1/chat",
        json={
            "question": "Show 4G cell inventory for Mumbai",
            "circle": "MH",
            "user_permitted_circles": ["DL"],
        },
    )
    assert r_unauth.status_code == 403

    # Cross-user result ownership check
    saved = default_result_store.save_result(
        owner_username="alice",
        report_id="RAN_CELL_4G",
        report_name="RAN 4G",
        circle="DL",
        domain="RAN",
        columns=[],
        rows=[],
        sources=[],
        applied_filters={},
        data_version="v1",
        data_as_of=None,
        mode="MOCK",
    )
    # Default non-admin caller is 'analyst_user'
    r_res = client.get(f"/v1/results/{saved.result_id}")
    assert r_res.status_code == 403


def test_excel_formula_injection_sanitized():
    assert sanitize_excel_cell("=CMD|' /C calc'!A0") == "'=CMD|' /C calc'!A0"
    assert sanitize_excel_cell("+SUM(A1:A2)") == "'+SUM(A1:A2)"
    assert sanitize_excel_cell("-1+1") == "'-1+1"
    assert sanitize_excel_cell("@SUM(1,2)") == "'@SUM(1,2)"
    assert sanitize_excel_cell("NormalText") == "NormalText"


def test_agent_testing_requires_developer_or_admin():
    # Non-admin rejected
    r_denied = client.post(
        "/v1/agents/test",
        json={"agent": "report_selector", "question": "Show 4G cells for Delhi"},
    )
    assert r_denied.status_code == 403

    # Admin token allowed (dev/test token containing 'admin')
    r_ok = client.post(
        "/v1/agents/test",
        json={"agent": "report_selector", "question": "Show 4G cells for Delhi"},
        headers={"Authorization": "Bearer netiq-admin-dev-token"},
    )
    assert r_ok.status_code == 200
    assert r_ok.json()["status"] == "SUCCESS"
    assert r_ok.json()["structured_json"]["report_id"] == "RAN_CELL_4G"
