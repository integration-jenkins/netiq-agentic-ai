"""Dynamic sidebar component populated from FastAPI metadata endpoints."""

from typing import Any
import streamlit as st

from api_client import NetiqApiClient, NetiqApiError
from session_manager import reset_conversation


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

        if st.button("New Conversation", use_container_width=True, type="primary"):
            reset_conversation()
            st.rerun()

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
        st.caption(f"Session: `{st.session_state.get('session_id')}`")
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
