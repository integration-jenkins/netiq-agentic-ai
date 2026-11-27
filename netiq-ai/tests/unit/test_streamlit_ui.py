"""Automated UI tests using Streamlit AppTest with mocked HTTP transport."""

import json
import sys
from pathlib import Path
import httpx
from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_APP_PATH = str(PROJECT_ROOT / "ui" / "streamlit" / "app.py")
UI_DIR = str(PROJECT_ROOT / "ui" / "streamlit")


def _answer(q: str) -> dict:
    return {
        "request_id": "req-1",
        "session_id": "c1",
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
    }


def _build_mock_handler(call_log: list[str], fail_backend: bool = False):
    saved: list[dict] = []  # chat "c1" as the backend stores it
    sessions: list[str] = []  # chatbot sessions handed out

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
        if path == "/v1/session/netiq":  # the backend asks NETIQ who owns the browser's NETIQ cookie
            if "JSESSIONID=good" not in request.headers.get("cookie", ""):
                return httpx.Response(401, json={"detail": "Not logged in to NETIQ."})
            sessions.append(f"sid-{len(sessions) + 1}")
            return httpx.Response(200, json={"session_id": sessions[-1], "user": {"username": "test123", "circleList": ["BR"]}})

        # Everything below needs a live chatbot session (only the newest one is live).
        if not sessions or request.headers.get("X-Session-ID") != sessions[-1]:
            return httpx.Response(401, json={"detail": "Not logged in or session expired."})
        if path == "/v1/conversations" and request.method == "GET":
            chats = [{"conversation_id": "c1", "title": saved[0]["content"], "summary": None,
                      "updated_at": "2026-11-26T09:00:00+00:00"}] if saved else []
            return httpx.Response(200, json={"username": "test123", "conversations": chats})
        if path == "/v1/conversations" and request.method == "POST":
            return httpx.Response(200, json={"conversation_id": "c1"})
        if path == "/v1/conversations/c1" and request.method == "GET":
            return httpx.Response(200, json={"conversation_id": "c1", "state": {}, "messages": saved})
        if path == "/v1/conversations/c1/messages":
            q = json.loads(request.content.decode("utf-8"))["question"]
            used = bool(saved)
            reply = {**_answer(q), "conversation_id": "c1", "history_used": used,
                     "history": f"User: {saved[-2]['content']}" if used else "", "circles_counted": []}
            saved.append({"role": "user", "content": q, "meta": {}, "created_at": "2026-11-26T09:00:00+00:00"})
            saved.append({"role": "assistant", "content": reply["answer"], "created_at": "2026-11-26T09:00:01+00:00",
                          "meta": {"history_used": used, "payload": reply}})
            return httpx.Response(200, json=reply)
        return httpx.Response(404)
    return handler


def _app(monkeypatch, handler, cookies: dict) -> AppTest:
    from ui.streamlit import api_client
    from ui.streamlit.components import login_panel

    mock_transport = httpx.MockTransport(handler)
    orig_init = api_client.NetiqApiClient.__init__

    def patched_init(self, config=None, api_key_override=None, transport=None, session_id=None):
        orig_init(self, config=config, api_key_override=api_key_override, transport=mock_transport, session_id=session_id)

    monkeypatch.setattr(api_client.NetiqApiClient, "__init__", patched_init)
    # The browser's cookies for this host name (NETIQ's JSESSIONID among them); change cookies["value"] in a test.
    monkeypatch.setattr(login_panel, "browser_cookie_header", lambda: cookies["value"])
    return AppTest.from_file(UI_APP_PATH, default_timeout=15)


def test_streamlit_renders_header_mock_banner_and_chat_flow(monkeypatch):
    call_log: list[str] = []
    cookies = {"value": ""}
    at = _app(monkeypatch, _build_mock_handler(call_log), cookies)
    at.run()
    assert not at.exception
    assert any("NETIQ Agentic AI" in t.value for t in at.title)
    assert not at.chat_input and not at.text_input  # no chat before the NETIQ login, and no login form
    assert any("Log in to NETIQ first" in w.value for w in at.warning)

    cookies["value"] = "JSESSIONID=expired"  # NETIQ does not know this cookie
    at.run()
    assert not at.chat_input and any("Log in to NETIQ first" in w.value for w in at.warning)

    cookies["value"] = "JSESSIONID=good"  # logged in to NETIQ, page reloaded
    at.run()
    assert not at.exception
    assert any("MOCK Data Mode Active" in w.value for w in at.warning)
    assert any("test123" in m.value for m in at.sidebar.markdown)
    assert not [b for b in at.sidebar.button if b.label == "Log out"]  # logging out happens in NETIQ

    # Submit a chat question: saved in a new chat, answered with a table
    at.chat_input[0].set_value("How many 4G cells are available in Bihar?").run()
    assert not at.exception
    assert any("Mock answer for: How many 4G cells are available in Bihar?" in m.value for m in at.markdown)
    assert len(at.dataframe) == 1
    assert any("Returned Records" == m.label for m in at.metric)
    assert any("New question, no history sent" in c.value for c in at.caption)
    assert at.session_state["conversation_id"] == "c1"

    # Verify rerun does not duplicate chat calls or metadata calls
    chat_calls_before = call_log.count("POST /v1/conversations/c1/messages")
    meta_calls_before = call_log.count("GET /v1/metadata/circles")
    at.run()
    assert call_log.count("POST /v1/conversations/c1/messages") == chat_calls_before
    assert call_log.count("GET /v1/metadata/circles") == meta_calls_before

    # A follow-up says the chat history was sent
    at.chat_input[0].set_value("and 5G?").run()
    assert any("Follow-up, so chat history was sent" in c.value for c in at.caption)

    # Test session reset ("New Conversation"), then open the saved chat from "My chats"
    new_chat_btn = [b for b in at.sidebar.button if b.label == "New Conversation"][0]
    new_chat_btn.click().run()
    assert len(at.session_state["messages"]) == 0 and at.session_state["conversation_id"] is None
    [b for b in at.sidebar.button if b.label == "How many 4G cells are available in Bihar?"][0].click().run()
    assert not at.exception
    assert len(at.session_state["messages"]) == 4 and len(at.dataframe) == 2  # saved answers keep their tables

    # The chatbot session ends (30 idle minutes) while NETIQ is still logged in: renewed quietly,
    # the open chat stays, and the unsent question can be sent with Retry.
    at.session_state["netiq_session"] = "sid-old"
    at.chat_input[0].set_value("and 3G?").run()
    assert not at.exception
    assert at.session_state["netiq_session"] == "sid-2" and at.session_state["conversation_id"] == "c1"
    assert any("Press Retry" in e.value for e in at.error)
    [b for b in at.button if b.label == "Retry Last Request"][0].click().run()
    assert any("Mock answer for: and 3G?" in m.value for m in at.markdown)


def test_streamlit_handles_backend_unavailable(monkeypatch):
    at = _app(monkeypatch, _build_mock_handler([], fail_backend=True), {"value": "JSESSIONID=good"})
    at.run()
    assert not at.exception
    assert any("Could not check your NETIQ login" in e.value for e in at.error)

    at.session_state["netiq_session"] = "sid-1"  # as if logged in before the backend went down
    at.run()
    assert not at.exception
    assert any("Backend: Disconnected" in e.value for e in at.sidebar.error)
