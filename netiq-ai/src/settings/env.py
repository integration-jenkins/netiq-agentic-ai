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
        default="http://localhost:8080",
        alias="NETIQ_API_BASE_URL",
        description="Base URL of the NETIQ Java Spring Boot backend"
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
    
    # Filesystem Paths Anchor Points
    project_root: Path = Field(default=PROJECT_ROOT, description="Absolute path to netiq-ai repository root")
    config_dir: Path = Field(default=PROJECT_ROOT / "configs", description="Path to configuration directory")
    fixtures_dir: Path = Field(default=PROJECT_ROOT / "data" / "fixtures", description="Path to synthetic test fixtures")
    reports_config_dir: Path = Field(default=PROJECT_ROOT / "configs" / "reports", description="Path to report catalog directory")


# Singleton settings instance accessible application-wide
settings = Settings()
