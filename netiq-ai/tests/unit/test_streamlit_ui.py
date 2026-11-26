"""Automated UI tests using Streamlit AppTest with mocked HTTP transport."""

import json
import sys
from pathlib import Path
import httpx
from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_APP_PATH = str(PROJECT_ROOT / "ui" / "streamlit" / "app.py")
UI_DIR = str(PROJECT_ROOT / "ui" / "streamlit")


def _build_mock_handler(call_log: list[str], fail_backend: bool = False):
    def handler(request: httpx.Request) -> httpx.Response:
        call_log.append(f"{request.method} {request.url.path}")
        if fail_backend:
            raise httpx.ConnectError("Backend offline")

        path = request.url.path
        if path == "/health":
            return httpx.Response(200, json={"status": "ok", "mode": "MOCK", "environment": "testing"})
        if path == "/v1/metadata/circles":
            return httpx.Response(200, json={"circles": ["BR", "DL", "MH"]})
        if path == "/v1/metadata/domains":
            return httpx.Response(200, json={"domains": ["RAN", "MW"]})
        if path == "/v1/metadata/reports":
            return httpx.Response(200, json={"reports": [{"id": "RAN_CELL_4G", "name": "RAN - Cell 4G", "domain": "RAN"}]})
        if path == "/v1/chat":
            body = json.loads(request.content.decode("utf-8"))
            q = body.get("question", "")
            return httpx.Response(200, json={
                "request_id": "req-1",
                "session_id": body.get("sessionId"),
                "result_id": "res-101",
                "status": "SUCCESS",
                "intent": "REPORT",
                "agent": "REPORT_AGENT",
                "answer": f"Mock answer for: {q}",
                "metrics": [{"label": "Returned Records", "value": 2}, {"label": "Total Records", "value": 2}],
                "table": {
                    "columns": [
                        {"field": "vendor", "label": "Vendor", "type": "string"},
                        {"field": "count", "label": "Count", "type": "integer"},
                    ],
                    "rows": [
                        {"vendor": "Ericsson", "count": 10},
                        {"vendor": "Nokia", "count": 5},
                    ],
                    "pagination": {"page": 0, "size": 50, "returnedRecords": 2, "totalRecords": 2, "hasNext": False},
                },
                "sources": [{
                    "reportId": "RAN_CELL_4G",
                    "reportName": "RAN - Cell 4G",
                    "circle": "BR",
                    "domain": "RAN",
                    "dataVersion": "BR_2026-11-26",
                    "dataAsOf": "2026-11-26T09:00:00+05:30",
                    "mode": "MOCK",
                }],
                "export": {"available": True, "resultId": "res-101", "formats": ["XLSX"]},
                "execution_time_ms": 42,
                "mode": "MOCK",
                "warnings": ["MOCK mode active."],
            })
        return httpx.Response(404)
    return handler


def test_streamlit_renders_header_mock_banner_and_chat_flow(monkeypatch):
    from ui.streamlit import api_client

    call_log: list[str] = []
    mock_transport = httpx.MockTransport(_build_mock_handler(call_log))
    orig_init = api_client.NetiqApiClient.__init__

    def patched_init(self, config=None, api_key_override=None, transport=None):
        orig_init(self, config=config, api_key_override=api_key_override, transport=mock_transport)

    monkeypatch.setattr(api_client.NetiqApiClient, "__init__", patched_init)

    at = AppTest.from_file(UI_APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception
    assert any("NETIQ Agentic AI" in t.value for t in at.title)
    assert any("MOCK Data Mode Active" in w.value for w in at.warning)

    # Submit a chat question
    at.chat_input[0].set_value("How many 4G cells are available in Bihar?").run()
    assert not at.exception
    assert any("Mock answer for: How many 4G cells are available in Bihar?" in m.value for m in at.markdown)
    assert len(at.dataframe) == 1
    assert any("Returned Records" == m.label for m in at.metric)

    # Verify rerun does not duplicate /v1/chat calls or metadata calls
    chat_calls_before = call_log.count("POST /v1/chat")
    meta_calls_before = call_log.count("GET /v1/metadata/circles")
    at.run()
    assert call_log.count("POST /v1/chat") == chat_calls_before
    assert call_log.count("GET /v1/metadata/circles") == meta_calls_before

    # Test session reset ("New Conversation")
    new_chat_btn = [b for b in at.sidebar.button if b.label == "New Conversation"][0]
    new_chat_btn.click().run()
    assert len(at.session_state["messages"]) == 0


def test_streamlit_handles_backend_unavailable(monkeypatch):
    from ui.streamlit import api_client

    call_log: list[str] = []
    mock_transport = httpx.MockTransport(_build_mock_handler(call_log, fail_backend=True))
    orig_init = api_client.NetiqApiClient.__init__

    def patched_init(self, config=None, api_key_override=None, transport=None):
        orig_init(self, config=config, api_key_override=api_key_override, transport=mock_transport)

    monkeypatch.setattr(api_client.NetiqApiClient, "__init__", patched_init)

    at = AppTest.from_file(UI_APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception
    assert any("Backend: Disconnected" in e.value for e in at.sidebar.error)
