"""Main chat panel rendering conversation history, dynamic tables, metrics, sources, and exports."""

from typing import Any
import streamlit as st

from ui.streamlit.api_client import NetiqApiClient, NetiqApiError
from ui.streamlit.components.charts import render_charts
from ui.streamlit.components.data_table import render_data_table
from ui.streamlit.components.error_panel import render_error_panel
from ui.streamlit.components.export_panel import render_export_panel
from ui.streamlit.components.metric_cards import render_metric_cards
from ui.streamlit.components.source_panel import render_source_panel
from ui.streamlit.session_manager import SESSION_ENDED, append_assistant_response, append_user_message, end_login

EXAMPLE_QUESTIONS = [
    "How many 4G cells are available in Bihar?",
    "Show duplicate MW nodes grouped by vendor",
    "Compare RAN inventory between Delhi and Haryana",
    "Show MW transmission links with capacity information",
    "Explain the difference between CPLANE and UPLANE",
]


def _execute_question(question: str, api_client: NetiqApiClient) -> None:
    """Send a question to the user's saved chat (the backend saves it and gets the answer)."""
    append_user_message(question)
    st.session_state["last_failed_question"] = None
    with st.spinner("Querying NETIQ Agentic AI..."):
        try:
            if not st.session_state.get("conversation_id"):  # a new chat is saved with its first question
                st.session_state["conversation_id"] = api_client.create_conversation()
            resp = api_client.send_message(
                conversation_id=st.session_state["conversation_id"],
                question=question,
                circle=st.session_state.get("selected_circle"),
                domain=st.session_state.get("selected_domain"),
                report_id=st.session_state.get("selected_report_id"),
                size=st.session_state.get("page_size", 50),
            )
            append_assistant_response(resp)
            st.session_state["chats"] = None  # title and order in "My chats" change
        except NetiqApiError as err:
            if err.status_code == 401:
                end_login(SESSION_ENDED)  # renewed from the NETIQ login on the next run
            st.session_state["chats"] = None  # the question is saved even when the answer failed
            st.session_state["last_failed_question"] = {
                "question": question,
                "message": "Your session had ended, so this question was not sent. Press Retry to send it."
                if err.status_code == 401 else str(err),
                "status_code": err.status_code,
                "correlation_id": err.correlation_id,
            }


def render_chat_panel(api_client: NetiqApiClient) -> None:
    """Render conversation history, example prompts, and chat input."""
    messages = st.session_state.get("messages", [])

    if not messages:
        st.info("Ask a telecom inventory, comparison, or SOP knowledge question below, or pick an example:")
        cols = st.columns(len(EXAMPLE_QUESTIONS))
        for idx, example in enumerate(EXAMPLE_QUESTIONS):
            if cols[idx].button(example, key=f"ex_{idx}", use_container_width=True):
                _execute_question(example, api_client)
                st.rerun()

    for idx, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            # Safe markdown rendering (no unsafe HTML)
            st.markdown(msg.get("content", ""))

            # Short-term memory: was the earlier chat sent along with this question?
            if msg["role"] == "assistant" and msg.get("history_used") is not None:
                st.caption("Follow-up, so chat history was sent" if msg["history_used"]
                           else "New question, no history sent")
            if msg.get("history"):
                with st.expander("What the AI received as history with this question", expanded=False):
                    st.code(msg["history"], language=None)

            if msg["role"] == "assistant" and isinstance(msg.get("payload"), dict):
                payload: dict[str, Any] = msg["payload"]
                is_latest = idx == len(messages) - 1

                render_metric_cards(
                    metrics=payload.get("metrics", []),
                    execution_time_ms=payload.get("execution_time_ms"),
                )

                render_data_table(
                    table_payload=payload.get("table"),
                    result_id=payload.get("result_id"),
                    api_client=api_client,
                    is_latest_message=is_latest,
                    widget_key_prefix=f"msg_{idx}",
                )

                render_charts(payload.get("table"))

                render_source_panel(
                    sources=payload.get("sources", []),
                    applied_filters=payload.get("applied_filters"),
                    warnings=payload.get("warnings"),
                    mode=payload.get("mode", "MOCK"),
                )

                render_export_panel(
                    export_info=payload.get("export"),
                    api_client=api_client,
                    widget_key_prefix=f"exp_{idx}",
                )

    failed = st.session_state.get("last_failed_question")
    if failed:
        render_error_panel(
            message=failed["message"],
            status_code=failed.get("status_code"),
            correlation_id=failed.get("correlation_id"),
            on_retry=lambda: (_execute_question(failed["question"], api_client), st.rerun()),
        )

    if prompt := st.chat_input("Ask a question about RAN, MW/UBR, FTTH, Wireline, Audit, or SOPs..."):
        _execute_question(prompt, api_client)
        st.rerun()
