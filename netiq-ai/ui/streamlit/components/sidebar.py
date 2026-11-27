"""Dynamic sidebar component populated from FastAPI metadata endpoints."""

from typing import Any
import streamlit as st

from ui.streamlit.api_client import NetiqApiClient, NetiqApiError
from ui.streamlit.session_manager import SESSION_ENDED, end_login, local_time, open_conversation, reset_conversation


def _render_user() -> None:
    """Who is logged in to NETIQ, and their circles. Logging out happens in NETIQ."""
    user = st.session_state.get("netiq_user") or {}
    circles = user.get("circleList") or []
    st.markdown(f"Logged in as **{user.get('username') or user.get('id') or 'unknown'}**")
    st.caption("Circles: " + (", ".join(map(str, circles)) if circles else "all (none set)"))


def _render_chats(api_client: NetiqApiClient) -> None:
    """My chats: newest first, with the one-line summary written after the user left the chat."""
    st.subheader("My chats")
    try:
        if st.session_state.get("chats") is None:
            st.session_state["chats"] = api_client.list_conversations()
    except NetiqApiError as err:
        if err.status_code == 401:
            end_login(SESSION_ENDED)
            st.rerun()
        st.caption(f"Could not load chats: {err}")
        return

    if not st.session_state["chats"]:
        st.caption("No chats yet. Ask a question to start one.")
    for chat in st.session_state["chats"]:
        cid = chat["conversation_id"]
        title = chat.get("title") or "Untitled chat"
        is_open = cid == st.session_state.get("conversation_id")
        if st.button(title[:60], key=f"chat_{cid}", use_container_width=True,
                     type="primary" if is_open else "secondary", help=title):
            try:
                open_conversation(cid, api_client.get_conversation(cid).get("messages", []))
            except NetiqApiError as err:
                if err.status_code == 401:
                    end_login(SESSION_ENDED)
                else:
                    st.session_state["chats"] = None  # e.g. the chat was deleted after 30 days unused
            st.rerun()
        st.caption(" · ".join(x for x in (chat.get("summary"), local_time(chat.get("updated_at"))) if x))


def _load_metadata_once(api_client: NetiqApiClient) -> dict[str, Any]:
    """Fetch and cache metadata once per session to avoid rerun API churn."""
    cache = st.session_state.get("metadata_cache", {})
    if cache.get("loaded"):
        return cache

    try:
        health = api_client.get_health(details=False)
        circles = api_client.get_circles()
        domains = api_client.get_domains()
        reports = api_client.get_reports()
        cache = {
            "loaded": True,
            "backend_ok": health.get("status") == "ok",
            "mode": health.get("mode", "MOCK"),
            "environment": health.get("environment", "development"),
            "circles": circles,
            "domains": domains,
            "reports": reports,
        }
        st.session_state["metadata_cache"] = cache
    except NetiqApiError as err:
        cache = {
            "loaded": False,
            "backend_ok": False,
            "error": str(err),
            "mode": "UNKNOWN",
            "environment": "unknown",
            "circles": [],
            "domains": [],
            "reports": [],
        }
    return cache


def render_sidebar(api_client: NetiqApiClient) -> dict[str, Any]:
    """Render sidebar filters, controls, and health indicator."""
    with st.sidebar:
        st.header("NETIQ Controls")
        _render_user()

        if st.button("New Conversation", use_container_width=True, type="primary"):
            reset_conversation()
            st.rerun()

        _render_chats(api_client)
        st.divider()

        if st.button("Refresh Metadata", use_container_width=True):
            st.session_state["metadata_cache"] = {}
            st.rerun()

        meta = _load_metadata_once(api_client)

        if meta.get("backend_ok"):
            st.success(f"Backend: Connected ({meta.get('mode')})")
        else:
            st.error("Backend: Disconnected")
            if meta.get("error"):
                st.caption(meta["error"])

        st.divider()

        # Dynamic Circle Selection
        circle_options = ["(Auto / All)"] + meta.get("circles", [])
        sel_circle = st.selectbox("Circle", options=circle_options, index=0)
        st.session_state["selected_circle"] = None if sel_circle == "(Auto / All)" else sel_circle

        # Dynamic Domain Selection
        domain_options = ["(All Domains)"] + meta.get("domains", [])
        sel_domain = st.selectbox("Domain", options=domain_options, index=0)
        selected_domain = None if sel_domain == "(All Domains)" else sel_domain
        st.session_state["selected_domain"] = selected_domain

        # Dynamic Report Selection filtered by Domain
        all_reports = meta.get("reports", [])
        filtered_reports = [
            r for r in all_reports
            if not selected_domain or r.get("domain") == selected_domain
        ]
        report_labels = ["(Auto-Select Report)"] + [
            f"{r.get('id')} — {r.get('name')}" for r in filtered_reports
        ]
        sel_report_label = st.selectbox("Optional Report", options=report_labels, index=0)
        if sel_report_label == "(Auto-Select Report)":
            st.session_state["selected_report_id"] = None
        else:
            st.session_state["selected_report_id"] = sel_report_label.split(" — ", 1)[0]

        st.divider()
        st.caption(f"Chat: `{st.session_state.get('conversation_id') or 'new (saved with the first question)'}`")
        msg_count = len([m for m in st.session_state.get("messages", []) if m["role"] == "user"])
        st.caption(f"Turns in chat: {msg_count}")

        # Optional API Key override for developer/admin testing
        with st.expander("Authentication (Optional)", expanded=False):
            api_key_val = st.text_input(
                "API Token / Key",
                value=st.session_state.get("api_key_input", ""),
                type="password",
                help="Required only when API auth is enforced or testing admin/developer endpoints.",
            )
            st.session_state["api_key_input"] = api_key_val

    return meta
