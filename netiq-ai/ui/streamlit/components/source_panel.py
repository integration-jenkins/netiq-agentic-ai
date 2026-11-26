"""Data source and evidence provenance panel."""

from typing import Any
import streamlit as st


def render_source_panel(
    sources: list[dict[str, Any]],
    applied_filters: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    mode: str = "MOCK",
) -> None:
    """Render traceable data sources, data date, version, and mode warnings."""
    if not sources and not warnings:
        return

    with st.expander("Data Sources & Evidence", expanded=False):
        if mode == "MOCK":
            st.warning("MOCK Mode Active: Results are served from offline synthetic test fixtures.")
        for w in warnings or []:
            st.info(str(w))

        if applied_filters:
            st.caption(f"Applied Filters: `{applied_filters}`")

        for idx, src in enumerate(sources or [], start=1):
            if len(sources) > 1:
                st.markdown(f"**Source {idx}**")
            data_date = src.get("dataAsOf") or "Data date unavailable."
            data_ver = src.get("dataVersion") or "Unavailable"
            cols = st.columns(3)
            with cols[0]:
                if src.get("docId"):
                    st.write(f"**Doc ID:** `{src.get('docId')}`")
                else:
                    st.write(f"**Report ID:** `{src.get('reportId') or 'N/A'}`")
                st.write(f"**Name:** {src.get('reportName') or 'N/A'}")
            with cols[1]:
                st.write(f"**Circle:** `{src.get('circle') or 'All / Unspecified'}`")
                st.write(f"**Domain:** `{src.get('domain') or 'N/A'}`")
            with cols[2]:
                st.write(f"**Data Date:** `{data_date}`")
                st.write(f"**Data Version:** `{data_ver}`")
                st.write(f"**Mode:** `{src.get('mode', mode)}`")
