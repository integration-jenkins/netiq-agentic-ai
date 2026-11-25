"""Session management (task 1.6) through the API, using the real NETIQ login session store."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.security import netiq_login
from src.session import chat_store, chat_summary

client = TestClient(create_app())
LOGIN = {"username": "test123", "id": "test123", "role": None, "permissions": [], "circleList": []}


class FakeLLM:  # stands in for Ollama so the tests never call a real model
    def __init__(self, *args, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *exc): pass
    async def generate(self, prompt, **kwargs): return SimpleNamespace(response_text="Asked about 4G cells in MU.")


@pytest.fixture(autouse=True)
def chat_db(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAT_DB_PATH", str(tmp_path / "chat.db"))
    monkeypatch.setattr(chat_summary, "OllamaProvider", FakeLLM)


@pytest.fixture
def session():
    sid = netiq_login._create_session(dict(LOGIN))  # what a NETIQ login leaves behind
    yield {"X-Session-ID": sid}
    netiq_login.logout(sid)


def test_routes_need_a_login_session():
    assert client.get("/v1/conversations").status_code == 401
    assert client.post("/v1/conversations", headers={"X-Session-ID": "made-up"}).status_code == 401


def test_chat_flow_keeps_history_for_follow_ups(session):
    chat = client.post("/v1/conversations", headers=session).json()["conversation_id"]
    first = client.post(f"/v1/conversations/{chat}/messages", headers=session,
                        json={"question": "how many 4G cells in Mumbai?", "circle": "Mumbai"}).json()
    second = client.post(f"/v1/conversations/{chat}/messages", headers=session, json={"question": "and 5G?"}).json()
    assert first["history_used"] is False and second["history_used"] is True
    assert second["history"] == "User: how many 4G cells in Mumbai?"  # the placeholder reply is not sent as history

    opened = client.get(f"/v1/conversations/{chat}", headers=session).json()
    assert [m["role"] for m in opened["messages"]] == ["user", "assistant", "user", "assistant"]
    listed = client.get("/v1/conversations", headers=session).json()
    assert listed["username"] == "test123" and listed["conversations"][0]["title"] == "how many 4G cells in Mumbai?"


def test_circles_count_from_the_box_and_the_question(session):
    chat = client.post("/v1/conversations", headers=session).json()["conversation_id"]
    ask = lambda body: client.post(f"/v1/conversations/{chat}/messages", headers=session, json=body).json()
    assert ask({"question": "how many 4G cells in Mumbai?", "circle": "Mumbai"})["circles_counted"] == ["MU"]  # once
    assert ask({"question": "how many sites in Gujarat ?"})["circles_counted"] == ["GJ"]  # only in the question
    assert ask({"question": "and 5G?"})["circles_counted"] == []
    assert {k["keyword"]: k["hits"] for k in chat_store.top_keywords("test123")} == {"MU": 1, "GJ": 1}


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
