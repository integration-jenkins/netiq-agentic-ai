"""Streamlit session_state manager for conversation, pagination, export, and metadata caching."""

import uuid
from typing import Any
import streamlit as st


def init_session_state() -> None:
    """Initialize required Streamlit session state keys deterministically."""
    st.session_state.setdefault("session_id", f"session-{uuid.uuid4().hex[:10]}")
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
    st.session_state["session_id"] = f"session-{uuid.uuid4().hex[:10]}"
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
    })
    if response_payload.get("result_id"):
        st.session_state["current_result_id"] = response_payload["result_id"]
        st.session_state["page_number"] = 0
        st.session_state["table_search"] = ""
