"""Environment-backed settings for NETIQ Agentic AI."""

from enum import Enum
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ApiMode(str, Enum):
    MOCK = "MOCK"
    LIVE = "LIVE"


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application-wide settings with offline fail-closed defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnvironment = Field(default=AppEnvironment.DEVELOPMENT, alias="APP_ENV")
    netiq_api_mode: ApiMode = Field(default=ApiMode.MOCK, alias="NETIQ_API_MODE")
    netiq_api_base_url: str = Field(
        default="http://localhost:8080", alias="NETIQ_API_BASE_URL"
    )
    netiq_api_timeout_seconds: float = Field(
        default=10.0, alias="NETIQ_API_TIMEOUT_SECONDS"
    )
    netiq_api_auth_token: str | None = Field(default=None, alias="NETIQ_API_AUTH_TOKEN")
    
    # Path settings
    project_root: Path = Field(default=PROJECT_ROOT)
    config_dir: Path = Field(default=PROJECT_ROOT / "configs")
    fixtures_dir: Path = Field(default=PROJECT_ROOT / "data" / "fixtures")
    reports_config_dir: Path = Field(default=PROJECT_ROOT / "configs" / "reports")


settings = Settings()
