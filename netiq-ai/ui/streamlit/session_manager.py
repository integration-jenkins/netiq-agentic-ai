"""Streamlit session_state manager for login, saved chats, pagination, export, and metadata caching.

Chats are saved on the backend per NETIQ user (/v1/conversations). Here we only keep the chatbot
session id (taken from the NETIQ login, see components/login_panel.py), the open chat and its
messages for this browser tab.
"""

from datetime import datetime
from typing import Any
import streamlit as st

SESSION_ENDED = ("Your session ended: you logged out of NETIQ, or 30 minutes passed without activity. "
                 "Your chats are saved.")


def init_session_state() -> None:
    """Initialize required Streamlit session state keys deterministically."""
    st.session_state.setdefault("netiq_session", None)  # NETIQ login session id (X-Session-ID)
    st.session_state.setdefault("netiq_user", {})  # NETIQ login reply: username, circleList, ...
    st.session_state.setdefault("login_note", None)
    st.session_state.setdefault("conversation_id", None)  # open saved chat; None = new chat, saved on first question
    st.session_state.setdefault("chats", None)  # the user's saved chats; None = load again
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("selected_circle", None)
    st.session_state.setdefault("selected_domain", None)
    st.session_state.setdefault("selected_report_id", None)
    st.session_state.setdefault("current_result_id", None)
    st.session_state.setdefault("page_number", 0)
    st.session_state.setdefault("page_size", 50)
    st.session_state.setdefault("table_search", "")
    st.session_state.setdefault("export_cache", {})  # {result_id: {fileId, fileName, bytes}}
    st.session_state.setdefault("metadata_cache", {})
    st.session_state.setdefault("api_key_input", "")
    st.session_state.setdefault("last_failed_question", None)


def reset_conversation() -> None:
    """Start a fresh conversation while keeping cached metadata and auth key."""
    st.session_state["conversation_id"] = None  # the backend saves it when the first question is sent
    st.session_state["messages"] = []
    st.session_state["current_result_id"] = None
    st.session_state["page_number"] = 0
    st.session_state["table_search"] = ""
    st.session_state["export_cache"] = {}
    st.session_state["last_failed_question"] = None


def append_user_message(question: str) -> None:
    st.session_state["messages"].append({"role": "user", "content": question})


def append_assistant_response(response_payload: dict[str, Any]) -> None:
    st.session_state["messages"].append({
        "role": "assistant",
        "content": response_payload.get("answer", ""),
        "payload": response_payload,
        "history_used": response_payload.get("history_used"),
        "history": response_payload.get("history") or "",  # what was sent as chat history with this question
    })
    if response_payload.get("result_id"):
        st.session_state["current_result_id"] = response_payload["result_id"]
        st.session_state["page_number"] = 0
        st.session_state["table_search"] = ""


def start_login(session_id: str, user: dict[str, Any]) -> None:
    previous = (st.session_state.get("netiq_user") or {}).get("username")
    st.session_state["netiq_session"] = session_id
    st.session_state["netiq_user"] = user or {}
    st.session_state["login_note"] = None
    st.session_state["chats"] = None
    if (user or {}).get("username") != previous:
        reset_conversation()  # another user: never show the previous user's open chat


def end_login(note: str | None = None) -> None:
    """The backend said 401: the session is checked against NETIQ again on the next run. The open
    chat stays on screen, so after a silent renewal (still logged in to NETIQ) the user goes on."""
    st.session_state["netiq_session"] = None
    st.session_state["login_note"] = note
    st.session_state["chats"] = None


def open_conversation(conversation_id: str, messages: list[dict[str, Any]]) -> None:
    """Show a saved chat: its messages as the backend stored them (answers with their tables)."""
    reset_conversation()
    st.session_state["conversation_id"] = conversation_id
    for m in messages:
        meta = m.get("meta") or {}
        st.session_state["messages"].append({
            "role": m["role"],
            "content": m.get("content", ""),
            "payload": meta.get("payload"),
            "history_used": meta.get("history_used"),
        })
        if (meta.get("payload") or {}).get("result_id"):
            st.session_state["current_result_id"] = meta["payload"]["result_id"]


def local_time(iso: str | None) -> str:
    """Backend UTC time -> short local time for the chat list."""
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%d %b, %H:%M")
    except (TypeError, ValueError):
        return ""
