"""Fail-closed YAML configuration loader for NETIQ Agentic AI.

Architecture Role:
------------------
This module provides safe, cached loading of YAML configuration files from `configs/`.
It implements a fail-closed policy: if a required configuration file is missing,
inaccessible, or contains malformed YAML syntax, it immediately raises a `ConfigurationError`
rather than falling back to unvalidated defaults.

Key Functions:
--------------
- `load_yaml_file`: Base safe file reader.
- `load_limits_config`: Loads pagination, HTTP timeouts, and retrieval bounds.
- `load_allowed_apis_config`: Loads the exact method/path allowlist.
- `load_catalog_config`: Loads the master report catalogue and reconciliation logs.
- `load_report_definition`: Resolves individual report definitions from domain files.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any
import yaml

from src.settings.env import settings


class ConfigurationError(Exception):
    """Raised when configuration files cannot be loaded, are missing, or contain invalid syntax."""
    pass


def load_yaml_file(path: Path) -> Any:
    """Safely load and parse a YAML file fail-closed.
    
    Args:
        path: Path to the YAML file.
        
    Returns:
        Parsed YAML content (typically a dictionary or list).
        
    Raises:
        ConfigurationError: If the file does not exist or contains invalid YAML.
    """
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
    """Load runtime limits configuration from `configs/limits.yaml`.
    
    Cached to minimize filesystem I/O during high-frequency query evaluation.
    """
    path = settings.config_dir / "limits.yaml"
    data = load_yaml_file(path)
    if "limits" not in data:
        raise ConfigurationError(f"Malformed limits configuration in {path}: 'limits' key missing")
    return data["limits"]


@lru_cache(maxsize=1)
def load_allowed_apis_config() -> list[dict[str, Any]]:
    """Load approved API allowlist from `configs/allowed_apis.yaml`.
    
    Cached for fast perimeter evaluation by AllowlistPolicy.
    """
    path = settings.config_dir / "allowed_apis.yaml"
    data = load_yaml_file(path)
    if not isinstance(data, dict) or "allowed_apis" not in data:
        raise ConfigurationError(f"Malformed allowed_apis configuration in {path}: 'allowed_apis' key missing")
    return data.get("allowed_apis", [])


@lru_cache(maxsize=1)
def load_catalog_config() -> dict[str, Any]:
    """Load master report catalog configuration from `configs/reports/catalog.yaml`."""
    path = settings.reports_config_dir / "catalog.yaml"
    data = load_yaml_file(path)
    if not isinstance(data, dict) or "reports" not in data:
        raise ConfigurationError(f"Malformed catalog configuration in {path}: 'reports' key missing")
    return data


def load_report_definition(report_id: str) -> dict[str, Any]:
    """Load an individual report definition by report ID or report code.
    
    Searches `catalog.yaml` and follows `file_path` to load the complete domain YAML.
    
    Args:
        report_id: Unique identifier (e.g., 'RAN_CELL_4G') or report code (e.g., '4g').
        
    Returns:
        dict: Complete report definition metadata.
        
    Raises:
        ConfigurationError: If report ID is not registered in the catalog.
    """
    catalog = load_catalog_config()
    for report in catalog.get("reports", []):
        if report.get("id") == report_id or report.get("report_code") == report_id:
            file_path_str = report.get("file_path")
            if file_path_str:
                domain_path = settings.project_root / file_path_str
                if domain_path.is_file():
                    return load_yaml_file(domain_path)
            return report
    raise ConfigurationError(f"Report ID '{report_id}' not found in catalog")


def clear_config_cache() -> None:
    """Clear cached configurations (used during testing to force reload)."""
    load_limits_config.cache_clear()
    load_allowed_apis_config.cache_clear()
    load_catalog_config.cache_clear()
