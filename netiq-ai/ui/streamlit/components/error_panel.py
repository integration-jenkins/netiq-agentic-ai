"""Standardized safe error display and retry component."""

from typing import Callable
import streamlit as st


def render_error_panel(
    message: str,
    status_code: int | None = None,
    correlation_id: str | None = None,
    on_retry: Callable[[], None] | None = None,
) -> None:
    """Display safe error details without exposing internal stack traces or secrets."""
    prefix = f"[HTTP {status_code}] " if status_code else ""
    st.error(f"{prefix}{message}")
    if correlation_id:
        st.caption(f"Correlation ID: `{correlation_id}`")
    if on_retry is not None:
        if st.button("Retry Last Request", key=f"retry_{correlation_id or 'err'}"):
            on_retry()
