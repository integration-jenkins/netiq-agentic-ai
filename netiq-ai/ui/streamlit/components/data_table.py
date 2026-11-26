"""Dynamic, paginated report table component powered by backend column metadata."""

from typing import Any
import pandas as pd
import streamlit as st

from api_client import NetiqApiClient, NetiqApiError


def _build_column_config(columns: list[dict[str, Any]]) -> dict[str, Any]:
    """Map API column metadata to Streamlit column_config objects."""
    cfg: dict[str, Any] = {}
    for col in columns:
        field = col.get("field")
        label = col.get("label") or field
        ctype = (col.get("type") or "string").lower()
        if not field:
            continue
        if ctype == "integer":
            cfg[field] = st.column_config.NumberColumn(label=label, format="%d")
        elif ctype == "float":
            cfg[field] = st.column_config.NumberColumn(label=label, format="%.2f")
        elif ctype in ("date", "datetime"):
            cfg[field] = st.column_config.TextColumn(label=label)
        else:
            cfg[field] = st.column_config.TextColumn(label=label)
    return cfg


def render_data_table(
    table_payload: dict[str, Any] | None,
    result_id: str | None,
    api_client: NetiqApiClient,
    is_latest_message: bool = False,
    widget_key_prefix: str = "tbl",
) -> None:
    """Render dynamic st.dataframe() with optional server-side pagination and search."""
    if not table_payload:
        return

    columns = table_payload.get("columns", [])
    rows = table_payload.get("rows", [])
    pagination = table_payload.get("pagination") or {}

    # Interactive server-side pagination & search for the active result
    if is_latest_message and result_id:
        col_search, col_size = st.columns([3, 1])
        with col_search:
            search_val = st.text_input(
                "Filter current result",
                value=st.session_state.get("table_search", ""),
                placeholder="Search across columns...",
                key=f"{widget_key_prefix}_search",
            )
        with col_size:
            page_size = st.selectbox(
                "Page size",
                options=[10, 25, 50, 100],
                index=[10, 25, 50, 100].index(st.session_state.get("page_size", 50))
                if st.session_state.get("page_size", 50) in [10, 25, 50, 100]
                else 2,
                key=f"{widget_key_prefix}_size",
            )

        current_page = st.session_state.get("page_number", 0)
        if search_val != st.session_state.get("table_search", ""):
            st.session_state["table_search"] = search_val
            st.session_state["page_number"] = 0
            current_page = 0
        if page_size != st.session_state.get("page_size", 50):
            st.session_state["page_size"] = page_size
            st.session_state["page_number"] = 0
            current_page = 0

        # Fetch requested page from backend only when paginated/filtered away from initial page 0
        if current_page > 0 or search_val or page_size != pagination.get("size", 50):
            try:
                page_resp = api_client.get_result_page(
                    result_id=result_id,
                    page=current_page,
                    size=page_size,
                    search=search_val or None,
                )
                columns = page_resp.get("columns", columns)
                rows = page_resp.get("rows", [])
                pagination = page_resp.get("pagination", pagination)
            except NetiqApiError as err:
                st.warning(f"Could not fetch page {current_page}: {err}")

    returned_count = pagination.get("returnedRecords", len(rows))
    total_count = pagination.get("totalRecords")
    page_num = pagination.get("page", 0)
    has_next = pagination.get("hasNext", False)

    total_display = str(total_count) if total_count is not None else "Unknown"
    st.caption(f"Showing **{returned_count}** records on page **{page_num + 1}** | Total matching records: **{total_display}**")

    if not rows:
        st.info("No records available for the current filter/page.")
        return

    df = pd.DataFrame(rows)
    ordered_fields = [c["field"] for c in columns if c.get("field") in df.columns]
    if ordered_fields:
        df = df[ordered_fields]

    st.dataframe(
        df,
        column_config=_build_column_config(columns),
        use_container_width=True,
        hide_index=True,
    )

    if is_latest_message and result_id:
        p_col1, p_col2, _ = st.columns([1, 1, 4])
        with p_col1:
            if st.button("Previous Page", disabled=page_num <= 0, key=f"{widget_key_prefix}_prev"):
                st.session_state["page_number"] = max(0, page_num - 1)
                st.rerun()
        with p_col2:
            if st.button("Next Page", disabled=not has_next, key=f"{widget_key_prefix}_next"):
                st.session_state["page_number"] = page_num + 1
                st.rerun()
