"""Main Streamlit application for NETIQ Agentic AI.

Run from project root:
    streamlit run ui/streamlit/app.py --server.address 127.0.0.1 --server.port 8501
"""

import sys
from pathlib import Path
import streamlit as st

# Ensure project root (netiq-ai/) is on sys.path for ui.streamlit.* imports
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui.streamlit.api_client import NetiqApiClient
from ui.streamlit.components.chat_panel import render_chat_panel
from ui.streamlit.components.sidebar import render_sidebar
from ui.streamlit.session_manager import init_session_state

st.set_page_config(
    page_title="NETIQ Agentic AI",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    """Render the NETIQ Agentic AI workspace."""
    init_session_state()

    api_key = st.session_state.get("api_key_input") or None
    client = NetiqApiClient(api_key_override=api_key)

    meta = render_sidebar(client)

    # Enterprise Header
    st.title("NETIQ Agentic AI")
    st.caption("Offline Telecom Inventory & Network Intelligence Assistant (API-Driven)")

    h_col1, h_col2, h_col3 = st.columns(3)
    with h_col1:
        st.metric("Backend Status", "Online" if meta.get("backend_ok") else "Offline")
    with h_col2:
        st.metric("Environment", str(meta.get("environment", "unknown")).upper())
    with h_col3:
        st.metric("Data Mode", str(meta.get("mode", "UNKNOWN")).upper())

    if meta.get("mode") == "MOCK":
        st.warning("MOCK Data Mode Active — Responses use offline synthetic fixtures; live NETIQ backend is not connected.")

    st.divider()
    render_chat_panel(client)


if __name__ == "__main__":
    main()
