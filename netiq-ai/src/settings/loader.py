"""Fail-closed YAML configuration loader."""

from functools import lru_cache
from pathlib import Path
from typing import Any
import yaml

from src.settings.env import settings


class ConfigurationError(Exception):
    """Raised when configuration files cannot be loaded or are invalid."""
    pass


def load_yaml_file(path: Path) -> Any:
    """Safely load and parse a YAML file fail-closed."""
    if not path.is_file():
        raise ConfigurationError(f"Required configuration file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
            return content if content is not None else {}
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML syntax in {path}: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Error reading configuration file {path}: {e}") from e


@lru_cache(maxsize=1)
def load_limits_config() -> dict[str, Any]:
    """Load limits configuration."""
    path = settings.config_dir / "limits.yaml"
    data = load_yaml_file(path)
    if "limits" not in data:
        raise ConfigurationError(f"Malformed limits configuration in {path}: 'limits' key missing")
    return data["limits"]


@lru_cache(maxsize=1)
def load_allowed_apis_config() -> list[dict[str, Any]]:
    """Load allowed APIs list fail-closed."""
    path = settings.config_dir / "allowed_apis.yaml"
    data = load_yaml_file(path)
    if not isinstance(data, dict) or "allowed_apis" not in data:
        raise ConfigurationError(f"Malformed allowed_apis configuration in {path}: 'allowed_apis' key missing")
    return data.get("allowed_apis", [])


@lru_cache(maxsize=1)
def load_catalog_config() -> dict[str, Any]:
    """Load report catalog configuration."""
    path = settings.reports_config_dir / "catalog.yaml"
    data = load_yaml_file(path)
    if not isinstance(data, dict) or "reports" not in data:
        raise ConfigurationError(f"Malformed catalog configuration in {path}: 'reports' key missing")
    return data


def load_report_definition(report_id: str) -> dict[str, Any]:
    """Load an individual report definition by report ID."""
    catalog = load_catalog_config()
    for report in catalog.get("reports", []):
        if report.get("id") == report_id or report.get("report_code") == report_id:
            # If report points to a domain file, load it; otherwise return entry
            file_path_str = report.get("file_path")
            if file_path_str:
                domain_path = settings.project_root / file_path_str
                if domain_path.is_file():
                    return load_yaml_file(domain_path)
            return report
    raise ConfigurationError(f"Report ID '{report_id}' not found in catalog")


def clear_config_cache() -> None:
    """Clear cached configurations (used during tests)."""
    load_limits_config.cache_clear()
    load_allowed_apis_config.cache_clear()
    load_catalog_config.cache_clear()
