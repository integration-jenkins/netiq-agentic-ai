"""Session management (task 1.6) through the API, using the real NETIQ login session store."""

from functools import partial
from types import MethodType, SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.orchestrator.chat_service import ChatService, default_chat_service
from src.api.app import create_app
from src.schemas.chat import ChatResponse
from src.security import netiq_login
from src.session import chat_store, chat_summary, identity
from src.tools.export.excel import default_excel_export_service

client = TestClient(create_app())
LOGIN = {"username": "test123", "id": "test123", "role": None, "permissions": [], "circleList": []}


class FakeLLM:  # stands in for Ollama so the tests never call a real model
    def __init__(self, *args, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *exc): pass
    async def generate(self, prompt, **kwargs): return SimpleNamespace(response_text="Asked about 4G cells in MU.")


async def fake_answer(request, user):  # stands in for the orchestrator (one test below uses the real one)
    return ChatResponse(request_id=request.request_id, session_id=request.session_id, answer=f"Answer for: {request.query}")


@pytest.fixture(autouse=True)
def chat_db(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAT_DB_PATH", str(tmp_path / "chat.db"))
    monkeypatch.setattr(chat_summary, "OllamaProvider", FakeLLM)
    monkeypatch.setattr(default_chat_service, "process_chat", fake_answer)


@pytest.fixture
def session():
    sid = netiq_login._create_session(dict(LOGIN))  # what a NETIQ login leaves behind
    yield {"X-Session-ID": sid}
    netiq_login.logout(sid)


def test_session_comes_from_the_netiq_login_cookie(monkeypatch):
    def netiq(request):  # NETIQ GET /auth/me: who owns this JSESSIONID?
        if request.url.path == "/auth/me" and request.headers.get("cookie") == "JSESSIONID=good":
            return httpx.Response(200, json={"username": "test123", "id": "test123", "role": None,
                                             "permissions": [], "circleList": ["BR"]})
        return httpx.Response(401)

    real = identity.session_from_netiq_cookie
    monkeypatch.setattr(identity, "session_from_netiq_cookie", partial(real, transport=httpx.MockTransport(netiq)))
    started = client.post("/v1/session/netiq", headers={"Cookie": "JSESSIONID=good"})
    assert started.status_code == 200 and started.json()["user"]["circleList"] == ["BR"]
    sid = started.json()["session_id"]
    try:
        listed = client.get("/v1/conversations", headers={"X-Session-ID": sid})
        assert listed.status_code == 200 and listed.json()["username"] == "test123"
    finally:
        netiq_login.logout(sid)
    assert client.post("/v1/session/netiq", headers={"Cookie": "JSESSIONID=old"}).status_code == 401
    assert client.post("/v1/session/netiq").status_code == 401  # no NETIQ cookie at all

    def down(request):
        raise httpx.ConnectError("NETIQ is not running")

    monkeypatch.setattr(identity, "session_from_netiq_cookie", partial(real, transport=httpx.MockTransport(down)))
    assert client.post("/v1/session/netiq", headers={"Cookie": "JSESSIONID=good"}).status_code == 503


def test_routes_need_a_login_session():
    assert client.get("/v1/conversations").status_code == 401
    assert client.post("/v1/conversations", headers={"X-Session-ID": "made-up"}).status_code == 401


def test_chat_flow_keeps_history_for_follow_ups(session):
    chat = client.post("/v1/conversations", headers=session).json()["conversation_id"]
    first = client.post(f"/v1/conversations/{chat}/messages", headers=session,
                        json={"question": "how many 4G cells in Mumbai?", "circle": "Mumbai"}).json()
    second = client.post(f"/v1/conversations/{chat}/messages", headers=session, json={"question": "and 5G?"}).json()
    assert first["history_used"] is False and second["history_used"] is True
    assert second["history"] == "User: how many 4G cells in Mumbai?\nAssistant: Answer for: how many 4G cells in Mumbai?"

    opened = client.get(f"/v1/conversations/{chat}", headers=session).json()
    assert [m["role"] for m in opened["messages"]] == ["user", "assistant", "user", "assistant"]
    assert opened["messages"][1]["meta"]["payload"]["answer"] == "Answer for: how many 4G cells in Mumbai?"
    listed = client.get("/v1/conversations", headers=session).json()
    assert listed["username"] == "test123" and listed["conversations"][0]["title"] == "how many 4G cells in Mumbai?"


def test_circles_count_from_the_box_and_the_question(session):
    chat = client.post("/v1/conversations", headers=session).json()["conversation_id"]
    ask = lambda body: client.post(f"/v1/conversations/{chat}/messages", headers=session, json=body).json()
    assert ask({"question": "how many 4G cells in Mumbai?", "circle": "Mumbai"})["circles_counted"] == ["MU"]  # once
    assert ask({"question": "how many sites in Gujarat ?"})["circles_counted"] == ["GJ"]  # only in the question
    assert ask({"question": "and 5G?"})["circles_counted"] == []
    assert {k["keyword"]: k["hits"] for k in chat_store.top_keywords("test123")} == {"MU": 1, "GJ": 1}


def test_a_failed_answer_is_saved_but_never_sent_as_history(session, monkeypatch):
    async def refuse(request, user):
        raise PermissionError("Not allowed for circle GJ.")

    chat = client.post("/v1/conversations", headers=session).json()["conversation_id"]
    monkeypatch.setattr(default_chat_service, "process_chat", refuse)
    refused = client.post(f"/v1/conversations/{chat}/messages", headers=session, json={"question": "how many sites in Gujarat ?"})
    assert refused.status_code == 403
    monkeypatch.setattr(default_chat_service, "process_chat", fake_answer)
    second = client.post(f"/v1/conversations/{chat}/messages", headers=session, json={"question": "and 5G?"}).json()
    assert second["history"] == "User: how many sites in Gujarat ?"
    saved = client.get(f"/v1/conversations/{chat}", headers=session).json()["messages"]
    assert saved[1]["meta"]["failed"] is True and [m["role"] for m in saved] == ["user", "assistant", "user", "assistant"]


def test_real_answer_is_saved_with_its_table_and_pages_and_exports_for_the_same_user(session, monkeypatch, tmp_path):
    monkeypatch.setattr(default_chat_service, "process_chat", MethodType(ChatService.process_chat, default_chat_service))
    monkeypatch.setattr(default_excel_export_service, "export_dir", tmp_path)  # keep test files out of data/exports
    chat = client.post("/v1/conversations", headers=session).json()["conversation_id"]
    reply = client.post(f"/v1/conversations/{chat}/messages", headers=session,
                        json={"question": "How many 4G cells are available in Bihar?"}).json()  # MOCK data, no LLM
    rid = reply["result_id"]
    assert reply["status"] == "SUCCESS" and reply["table"]["rows"] and rid

    saved = client.get(f"/v1/conversations/{chat}", headers=session).json()["messages"][1]["meta"]["payload"]
    assert saved["table"]["rows"] == reply["table"]["rows"] and "structured_data" not in saved

    assert client.get(f"/v1/results/{rid}", params={"page": 0, "size": 1}, headers=session).status_code == 200
    export = client.post("/v1/export", headers=session, json={"resultId": rid, "format": "XLSX"})
    assert export.status_code == 200
    assert client.get(f"/v1/export/{export.json()['fileId']}", headers=session).status_code == 200
    assert client.get(f"/v1/results/{rid}").status_code == 403  # the API-key user does not own this chat's result
    assert client.get(f"/v1/results/{rid}", headers={"X-Session-ID": "ended"}).status_code == 401  # no quiet switch


def test_leaving_a_chat_writes_its_summary(session):
    first = client.post("/v1/conversations", headers=session).json()["conversation_id"]
    client.post(f"/v1/conversations/{first}/messages", headers=session, json={"question": "how many 4G cells in Mumbai?"})
    assert client.get("/v1/conversations", headers=session).json()["conversations"][0]["summary"] is None  # in use
    second = client.post("/v1/conversations", headers=session).json()["conversation_id"]  # the user moves on
    summaries = {c["conversation_id"]: c["summary"] for c in client.get("/v1/conversations", headers=session).json()["conversations"]}
    assert summaries == {first: "Asked about 4G cells in MU.", second: None}


def test_session_cookie_works_too(session):
    client.cookies.set(netiq_login.SESSION_COOKIE, session["X-Session-ID"])
    try:
        assert client.get("/v1/conversations").status_code == 200
    finally:
        client.cookies.clear()


def test_another_user_cannot_open_the_chat(session):
    chat = client.post("/v1/conversations", headers=session).json()["conversation_id"]
    other = netiq_login._create_session({**LOGIN, "username": "someone_else", "id": "someone_else"})
    try:
        headers = {"X-Session-ID": other}
        assert client.get(f"/v1/conversations/{chat}", headers=headers).status_code == 404
        assert client.post(f"/v1/conversations/{chat}/messages", headers=headers, json={"question": "hi"}).status_code == 404
    finally:
        netiq_login.logout(other)


def test_logout_ends_access(session):
    assert client.get("/v1/conversations", headers=session).status_code == 200
    netiq_login.logout(session["X-Session-ID"])
    assert client.get("/v1/conversations", headers=session).status_code == 401


def test_idle_timeout_ends_access_but_keeps_the_chat(session, monkeypatch):
    chat = client.post("/v1/conversations", headers=session).json()["conversation_id"]
    timeout = netiq_login.SESSION_IDLE_TIMEOUT
    monkeypatch.setattr(netiq_login, "SESSION_IDLE_TIMEOUT", -1)  # as if 30 idle minutes passed
    assert client.get("/v1/conversations", headers=session).status_code == 401
    monkeypatch.setattr(netiq_login, "SESSION_IDLE_TIMEOUT", timeout)
    again = {"X-Session-ID": netiq_login._create_session(dict(LOGIN))}  # user logs in again
    try:
        assert client.get(f"/v1/conversations/{chat}", headers=again).status_code == 200
    finally:
        netiq_login.logout(again["X-Session-ID"])
