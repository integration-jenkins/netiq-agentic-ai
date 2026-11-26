"""Developer Agent Testing page powered exclusively by FastAPI APIs."""

import sys
from pathlib import Path
import streamlit as st

_UI_DIR = Path(__file__).resolve().parents[1]
if str(_UI_DIR) not in sys.path:
    sys.path.insert(0, str(_UI_DIR))

from api_client import NetiqApiClient, NetiqApiError
from session_manager import init_session_state

st.set_page_config(page_title="Agent Testing — NETIQ AI", page_icon="🧪", layout="wide")


def main() -> None:
    init_session_state()
    st.title("Developer Agent Testing")
    st.caption("Authorized developer/admin console for inspecting individual NETIQ agents and local Ollama inference.")

    api_key = st.text_input(
        "Developer / Admin Token",
        value=st.session_state.get("api_key_input", ""),
        type="password",
        help="Requires developer or admin credentials (e.g. token containing 'admin').",
    )
    st.session_state["api_key_input"] = api_key
    client = NetiqApiClient(api_key_override=api_key or None)

    try:
        agents = client.get_agents()
    except NetiqApiError as err:
        st.error(f"Could not load agents from backend: {err}")
        return

    agent_map = {f"{a['name']} ({a['id']})": a for a in agents}
    selected_label = st.selectbox("Select Agent", options=list(agent_map.keys()))
    selected_agent = agent_map[selected_label]

    st.info(f"**Purpose:** {selected_agent['description']} | **Configured Model:** `{selected_agent['configured_model']}`")

    question = st.text_area(
        "Test Question / Prompt",
        value="How many 4G cells are available in Bihar?",
        height=100,
    )
    circle = st.text_input("Optional Circle Filter (e.g. BR, DL)", value="")

    col1, col2 = st.columns(2)
    with col1:
        run_agent = st.button("Test Complete Agent (/v1/agents/test)", type="primary", use_container_width=True)
    with col2:
        run_raw_llm = st.button("Test Raw LLM Inference (/v1/inference)", use_container_width=True)

    if run_agent:
        with st.spinner(f"Executing {selected_agent['id']}..."):
            try:
                res = client.test_agent(
                    agent=selected_agent["id"],
                    question=question,
                    circle=circle.strip() or None,
                )
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Status", res.get("status"))
                c2.metric("Validation", res.get("validation_status"))
                c3.metric("Configured Model", res.get("configured_model"))
                c4.metric("Total Latency", f"{res.get('total_latency_ms', 0)} ms")

                if res.get("error"):
                    st.warning(f"Validation / Execution Notice: {res['error']}")

                st.subheader("Agent Output")
                st.write(res.get("output"))

                if res.get("structured_json") is not None:
                    st.subheader("Structured JSON Output")
                    st.json(res["structured_json"])

                if res.get("verified_model"):
                    with st.expander("Verified Model Identity & Token Usage", expanded=False):
                        st.json({
                            "verified_model": res["verified_model"],
                            "token_usage": res.get("token_usage", {}),
                            "inference_latency_ms": res.get("inference_latency_ms", 0),
                        })
            except NetiqApiError as err:
                st.error(f"Agent test rejected or failed (HTTP {err.status_code}): {err}")

    if run_raw_llm:
        with st.spinner("Executing raw /v1/inference..."):
            try:
                res = client.run_inference(prompt=question, role=selected_agent["role"])
                metrics = res.get("metrics", {})
                c1, c2, c3 = st.columns(3)
                c1.metric("Model", res.get("model"))
                c2.metric("Speed", f"{metrics.get('eval_tokens_per_second', 0)} tok/s")
                c3.metric("Latency", f"{metrics.get('total_duration_seconds', 0)} s")
                st.subheader("Raw Inference Response")
                st.write(res.get("response"))
            except NetiqApiError as err:
                st.error(f"Inference failed (HTTP {err.status_code}): {err}")


if __name__ == "__main__":
    main()
