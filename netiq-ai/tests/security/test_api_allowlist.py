"""Security tests for exact path-template allowlist and unsafe endpoint exclusion."""

import pytest
from src.adapters.netiq_http.allowed_api import (
    AllowlistPolicy,
    SecurityViolationError,
    UnverifiedContractError,
)


@pytest.fixture
def allowlist():
    return AllowlistPolicy()


def test_approved_report_endpoint_allowed_in_mock(allowlist):
    spec = allowlist.evaluate(method="POST", path="/api/nodes/reports/4g", mode="MOCK")
    assert spec["id"] == "netiq_inventory_reports"
    assert spec["read_only"] is True


def test_arbitrary_sql_endpoints_blocked(allowlist):
    with pytest.raises(SecurityViolationError, match="Access denied"):
        allowlist.evaluate(method="POST", path="/api/db-console/execute", mode="MOCK")

    with pytest.raises(SecurityViolationError, match="Access denied"):
        allowlist.evaluate(method="POST", path="/api/db-console/verify", mode="MOCK")


def test_import_and_upload_endpoints_blocked(allowlist):
    with pytest.raises(SecurityViolationError, match="Access denied"):
        allowlist.evaluate(method="POST", path="/api/data/import", mode="MOCK")

    with pytest.raises(SecurityViolationError, match="Access denied"):
        allowlist.evaluate(method="POST", path="/api/data/import/run", mode="MOCK")


def test_path_traversal_blocked(allowlist):
    with pytest.raises(SecurityViolationError, match="Malformed or unsafe path"):
        allowlist.evaluate(method="POST", path="/api/nodes/reports/../db-console/execute", mode="MOCK")


def test_query_string_injection_in_path_blocked(allowlist):
    with pytest.raises(SecurityViolationError, match="Malformed or unsafe path"):
        allowlist.evaluate(method="POST", path="/api/nodes/reports/4g?drop=table", mode="MOCK")


def test_unsupported_http_method_blocked(allowlist):
    with pytest.raises(SecurityViolationError, match="Access denied"):
        allowlist.evaluate(method="DELETE", path="/api/nodes/reports/4g", mode="MOCK")


def test_unregistered_endpoint_blocked(allowlist):
    with pytest.raises(SecurityViolationError, match="Access denied"):
        allowlist.evaluate(method="GET", path="/api/unregistered/random/path", mode="MOCK")
