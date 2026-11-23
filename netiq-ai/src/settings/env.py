"""Environment-backed runtime settings for NETIQ Agentic AI.

Architecture Role:
------------------
This module defines application-wide runtime configuration using `pydantic-settings`.
It parses environment variables (e.g., from `.env` or container environments) with
strict type validation and fail-closed defaults.

Key Settings:
-------------
- `APP_ENV`: Deployment stage (development, staging, production, testing).
- `NETIQ_API_MODE`: MOCK vs LIVE mode. Defaults to MOCK to guarantee offline safety.
- `NETIQ_API_BASE_URL`: Base URL for the Java Spring Boot backend service.
- `NETIQ_API_TIMEOUT_SECONDS`: Default socket timeout.
- `OLLAMA_BASE_URL`: Base URL for Ollama local inference server.
- `DEFAULT_LLM_MODEL`: Default LLM model name (configurable).
- `LLM_TIMEOUT_SECONDS`: Timeout for LLM generation requests.
- Project paths: Deterministic path anchors pointing to `configs/`, `data/fixtures/`,
  and `configs/reports/`.
"""

from enum import Enum
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    """Supported deployment lifecycle environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ApiMode(str, Enum):
    """Operational mode for backend telecom API integrations.
    
    - MOCK: Safe offline operation using version-controlled synthetic test fixtures.
    - LIVE: Direct HTTP interaction with deployed NETIQ Spring Boot services (gated).
    """
    MOCK = "MOCK"
    LIVE = "LIVE"


# Deterministic project root path anchor (two levels up from src/settings/env.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application-wide settings with offline fail-closed defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment and Execution Mode
    app_env: AppEnvironment = Field(
        default=AppEnvironment.DEVELOPMENT,
        alias="APP_ENV",
        description="Application lifecycle environment (development, staging, production, testing)"
    )
    netiq_api_mode: ApiMode = Field(
        default=ApiMode.MOCK,
        alias="NETIQ_API_MODE",
        description="API execution mode: MOCK (offline fixtures) or LIVE (backend HTTP)"
    )
    netiq_api_base_url: str = Field(
        default="http://localhost:6061",
        alias="NETIQ_API_BASE_URL",
        description="Base URL of the NETIQ Tomcat backend"
    )
    netiq_login_path: str = Field(
        default="/api/login",
        alias="NETIQ_LOGIN_PATH",
        description="NETIQ login API path"
    )
    netiq_login_method: str = Field(
        default="GET",
        alias="NETIQ_LOGIN_METHOD",
        description="NETIQ login HTTP method"
    )
    netiq_api_timeout_seconds: float = Field(
        default=10.0,
        alias="NETIQ_API_TIMEOUT_SECONDS",
        description="HTTP request timeout in seconds"
    )
    netiq_api_auth_token: str | None = Field(
        default=None,
        alias="NETIQ_API_AUTH_TOKEN",
        description="Bearer authentication token for backend integration"
    )

    # Security & Execution Governance Settings
    enforce_api_auth: bool = Field(
        default=False,
        alias="ENFORCE_API_AUTH",
        description="Whether to enforce API authentication token verification on all routes"
    )
    api_auth_token: str = Field(
        default="netiq-secure-token-2026",
        alias="NETIQ_APP_AUTH_TOKEN",
        description="Shared secret or bearer token accepted for client API requests"
    )
    max_prompt_chars: int = Field(
        default=8000,
        alias="MAX_PROMPT_CHARS",
        description="Maximum permissible prompt length in characters to prevent buffer exhaustion"
    )
    max_generation_tokens: int = Field(
        default=2048,
        alias="MAX_GENERATION_TOKENS",
        description="Maximum permissible token output count for LLM completions"
    )
    llm_max_concurrency: int = Field(
        default=4,
        alias="LLM_MAX_CONCURRENCY",
        description="Maximum concurrent LLM inference tasks allowed simultaneously"
    )
    live_sql_execution_enabled: bool = Field(
        default=False,
        alias="LIVE_SQL_EXECUTION_ENABLED",
        description="Strict safety gate: Live SQL execution against database is disabled by default"
    )
    vram_budget_gb: float = Field(
        default=8.0,
        alias="VRAM_BUDGET_GB",
        description="GPU VRAM budget for model allocation (RTX 5050 target: ~8 GB)"
    )

    # LLM and Ollama Settings (Configurable)
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        alias="OLLAMA_BASE_URL",
        description="Base URL for local Ollama daemon"
    )
    default_llm_model: str = Field(
        default="qwen3:4b-instruct-2507",
        alias="DEFAULT_LLM_MODEL",
        description="Configurable default LLM model name for local inference"
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        alias="LLM_TIMEOUT_SECONDS",
        description="Timeout for LLM inference requests in seconds"
    )
    
    # Filesystem Paths Anchor Points
    project_root: Path = Field(default=PROJECT_ROOT, description="Absolute path to netiq-ai repository root")
    config_dir: Path = Field(default=PROJECT_ROOT / "configs", description="Path to configuration directory")
    fixtures_dir: Path = Field(default=PROJECT_ROOT / "data" / "fixtures", description="Path to synthetic test fixtures")
    reports_config_dir: Path = Field(default=PROJECT_ROOT / "configs" / "reports", description="Path to report catalog directory")


# Singleton settings instance accessible application-wide
settings = Settings()
