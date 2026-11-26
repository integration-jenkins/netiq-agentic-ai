"""System Health & Diagnostics page powered exclusively by GET /health?details=true."""

import sys
from pathlib import Path
import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui.streamlit.api_client import NetiqApiClient, NetiqApiError
from ui.streamlit.session_manager import init_session_state

st.set_page_config(page_title="System Health — NETIQ AI", page_icon="🩺", layout="wide")


def main() -> None:
    init_session_state()
    st.title("System Health & Readiness")
    st.caption("Live diagnostics fetched exclusively via FastAPI (/health?details=true).")

    if st.button("Refresh Health Check"):
        st.rerun()

    api_key = st.session_state.get("api_key_input") or None
    client = NetiqApiClient(api_key_override=api_key)

    try:
        health = client.get_health(details=True)
    except NetiqApiError as err:
        st.error(f"FastAPI Backend Unreachable: {err}")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("FastAPI Status", "ONLINE" if health.get("fastapi_available") else "OFFLINE")
    c2.metric("Ollama Status", health.get("ollama_status", "UNKNOWN"))
    c3.metric("Data Mode", health.get("mode", "UNKNOWN"))
    c4.metric("Environment", str(health.get("environment", "unknown")).upper())

    st.divider()

    d1, d2 = st.columns(2)
    with d1:
        st.subheader("LLM & Knowledge Readiness")
        st.write(f"**Configured Primary Model:** `{health.get('configured_model')}`")
        st.write(f"**Configured Model Installed:** `{health.get('configured_model_available')}`")
        st.write(f"**Knowledge Base Ready:** `{health.get('knowledge_index_ready')}` ({health.get('knowledge_documents', 0)} documents)")
        st.write(f"**Live SQL Execution:** `{health.get('live_sql_enabled', False)}` (Safe Disabled by Default)")

    with d2:
        st.subheader("NETIQ Metadata & API Readiness")
        st.write(f"**Report Catalog Ready:** `{health.get('report_catalog_ready')}` ({health.get('report_count', 0)} reports)")
        st.write(f"**Java API Mode:** `{health.get('java_api_mode')}` (`{health.get('java_api_status')}`)")
        st.write(f"**Last Checked (UTC):** `{health.get('checked_at')}`")

    if health.get("installed_models") is not None:
        with st.expander("Administrator Diagnostics (Installed Local Models)", expanded=False):
            st.write(f"**Ollama URL:** `{health.get('ollama_base_url')}`")
            st.json(health.get("installed_models"))


if __name__ == "__main__":
    main()
