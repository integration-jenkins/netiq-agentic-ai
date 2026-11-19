"""Sample Streamlit local test panel. Run: streamlit run ui/streamlit/app.py"""
import uuid

import streamlit as st

st.title("NETIQ AI - Test Panel (sample)")
st.session_state.setdefault("session_id", str(uuid.uuid4()))
base_url = st.sidebar.text_input("API base URL", "http://localhost:8080")

if message := st.chat_input("Ask a question"):
    st.chat_message("user").write(message)
    st.chat_message("assistant").write(f"(sample) would POST to {base_url}/v1/chat")
