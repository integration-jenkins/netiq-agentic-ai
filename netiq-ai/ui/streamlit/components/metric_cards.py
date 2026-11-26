"""KPI and summary metric cards component."""

from typing import Any
import streamlit as st


def render_metric_cards(metrics: list[dict[str, Any]], execution_time_ms: int | None = None) -> None:
    """Render dynamic KPI cards from backend metrics array."""
    cards = list(metrics or [])
    if execution_time_ms is not None:
        cards.append({"label": "Latency", "value": f"{execution_time_ms} ms"})

    if not cards:
        return

    cols = st.columns(min(len(cards), 4))
    for idx, card in enumerate(cards):
        col = cols[idx % len(cols)]
        col.metric(label=str(card.get("label", "Metric")), value=card.get("value", "N/A"))
