"""Environment-backed configuration for the NETIQ Agentic AI Streamlit UI."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class UIConfig:
    """Configuration settings loaded strictly from environment variables."""
    api_base_url: str = os.getenv("NETIQ_AI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    api_key: str = os.getenv("NETIQ_AI_API_KEY", "")
    request_timeout: float = float(os.getenv("NETIQ_AI_REQUEST_TIMEOUT", "120"))
    metadata_timeout: float = float(os.getenv("NETIQ_AI_METADATA_TIMEOUT", "15"))
    default_page_size: int = int(os.getenv("NETIQ_AI_DEFAULT_PAGE_SIZE", "50"))
    netiq_web_url: str = os.getenv("NETIQ_WEB_URL", "").rstrip("/")  # NETIQ login page link; empty = this host, port 6061


def get_ui_config() -> UIConfig:
    """Return current UI configuration."""
    return UIConfig()
