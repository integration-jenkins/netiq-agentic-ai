"""Excel export panel calling FastAPI export and download APIs."""

from typing import Any
import streamlit as st

from ui.streamlit.api_client import NetiqApiClient, NetiqApiError

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def render_export_panel(
    export_info: dict[str, Any] | None,
    api_client: NetiqApiClient,
    widget_key_prefix: str = "exp",
) -> None:
    """Render Excel export generation and download controls."""
    if not export_info or not export_info.get("available"):
        return

    result_id = export_info.get("resultId")
    if not result_id:
        return

    cache = st.session_state.setdefault("export_cache", {})
    cached = cache.get(result_id)

    if cached:
        st.download_button(
            label=f"Download {cached['fileName']}",
            data=cached["bytes"],
            file_name=cached["fileName"],
            mime=XLSX_MIME,
            key=f"{widget_key_prefix}_dl_{result_id}",
        )
    else:
        if st.button("Prepare Excel Export (.xlsx)", key=f"{widget_key_prefix}_gen_{result_id}"):
            with st.spinner("Generating verified Excel workbook..."):
                try:
                    meta = api_client.generate_export(result_id)
                    file_id = meta["fileId"]
                    file_name = meta["fileName"]
                    content = api_client.download_export_bytes(file_id)
                    cache[result_id] = {
                        "fileId": file_id,
                        "fileName": file_name,
                        "bytes": content,
                    }
                    st.rerun()
                except NetiqApiError as err:
                    st.error(f"Export failed: {err}")
