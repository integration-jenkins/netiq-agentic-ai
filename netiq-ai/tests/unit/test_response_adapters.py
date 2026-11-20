"""Unit tests for response normalization adapter engine."""

import pytest
from src.adapters.netiq_http.response_adapters import (
    MalformedResponseError,
    PaginatedInventoryResponseAdapter,
    extract_dotted_path,
)
from src.schemas.reports import ReportMode, ReportStatus


def test_extract_dotted_path():
    data = {
        "nested": {"level1": {"target": 42}},
        "items": [{"name": "first"}, {"name": "second"}],
    }
    assert extract_dotted_path(data, "nested.level1.target") == 42
    assert extract_dotted_path(data, "items.1.name") == "second"
    assert extract_dotted_path(data, "nested.nonexistent", default="missing") == "missing"
    assert extract_dotted_path(None, "any.path") is None


def test_adapter_normalizes_standard_payload():
    adapter = PaginatedInventoryResponseAdapter({
        "response_mapping": {
            "rows_path": "data",
            "total_path": "pagination.totalRecords",
            "page_path": "pagination.page",
            "size_path": "pagination.size",
            "has_next_path": "hasNext",
            "field_aliases": {"cell_name": "cellName"},
        }
    })

    raw = {
        "success": True,
        "message": "OK",
        "hasNext": True,
        "data": [
            {"cell_id": "C1", "cell_name": "Cell_1"},
            {"cell_id": "C2", "cell_name": "Cell_2"},
        ],
        "pagination": {
            "page": 0,
            "size": 50,
            "totalRecords": 100,
        },
    }

    page = adapter.adapt(
        raw_json=raw,
        report_id="RAN_CELL_4G",
        domain="RAN",
        endpoint="/api/nodes/reports/4g",
        report_code="4g",
        mode=ReportMode.MOCK,
    )

    assert page.status == ReportStatus.SUCCESS
    assert len(page.data) == 2
    assert page.data[0]["cellName"] == "Cell_1"  # Alias normalized
    assert page.pagination.returnedRecords == 2
    assert page.pagination.totalRecords == 100
    assert page.pagination.hasNext is True


def test_adapter_handles_no_data_found():
    adapter = PaginatedInventoryResponseAdapter({
        "empty_result_message": "No Data Found!!",
        "response_mapping": {"rows_path": "data", "error_path": "message"},
    })

    raw = {
        "success": False,
        "message": "No Data Found!!",
        "data": [],
        "hasNext": False,
    }

    page = adapter.adapt(
        raw_json=raw,
        report_id="RAN_CELL_4G",
        domain="RAN",
        endpoint="/api/nodes/reports/4g",
        report_code="4g",
    )

    assert page.status == ReportStatus.EMPTY
    assert len(page.data) == 0
    assert page.pagination.returnedRecords == 0
    assert page.pagination.hasNext is False


def test_adapter_unknown_total_count_handled_as_none():
    adapter = PaginatedInventoryResponseAdapter({
        "response_mapping": {"rows_path": "data"},
    })

    raw = {
        "success": True,
        "data": [{"id": 1}],
        "hasNext": True,
    }

    page = adapter.adapt(
        raw_json=raw,
        report_id="RAN_TEST",
        domain="RAN",
        endpoint="/api/test",
        report_code="test",
    )

    assert page.pagination.totalRecords is None
    assert page.pagination.returnedRecords == 1
    assert page.pagination.hasNext is True


def test_adapter_malformed_non_dict_raises():
    adapter = PaginatedInventoryResponseAdapter()
    with pytest.raises(MalformedResponseError):
        adapter.adapt(
            raw_json=["not", "a", "dict"],  # type: ignore
            report_id="RAN_TEST",
            domain="RAN",
            endpoint="/api/test",
            report_code="test",
        )


def test_adapter_missing_rows_path_raises():
    adapter = PaginatedInventoryResponseAdapter({
        "response_mapping": {"rows_path": "nonexistent_field"},
    })
    raw = {"success": True, "items": [{"id": 1}]}
    with pytest.raises(MalformedResponseError, match="Rows path 'nonexistent_field' was not found"):
        adapter.adapt(
            raw_json=raw,
            report_id="RAN_TEST",
            domain="RAN",
            endpoint="/api/test",
            report_code="test",
        )
