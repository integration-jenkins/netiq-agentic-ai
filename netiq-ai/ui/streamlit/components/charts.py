"""Safe, metadata-driven chart rendering for verified numeric aggregations."""

from typing import Any
import pandas as pd
import streamlit as st


def render_charts(table_payload: dict[str, Any] | None) -> None:
    """Render a bar chart only when verified categorical + numeric columns exist."""
    if not table_payload:
        return

    columns = table_payload.get("columns", [])
    rows = table_payload.get("rows", [])
    if not rows or len(rows) < 2 or len(rows) > 25:
        return

    cat_cols = [c["field"] for c in columns if (c.get("type") or "").lower() == "string"]
    num_cols = [c["field"] for c in columns if (c.get("type") or "").lower() in ("integer", "float")]

    if not cat_cols or not num_cols:
        return

    label_col = cat_cols[0]
    metric_col = num_cols[0]

    df = pd.DataFrame(rows)
    if label_col not in df.columns or metric_col not in df.columns:
        return

    if not pd.api.types.is_numeric_dtype(df[metric_col]):
        return

    with st.expander("Visual Breakdown", expanded=False):
        chart_df = df[[label_col, metric_col]].dropna().set_index(label_col)
        st.bar_chart(chart_df)
