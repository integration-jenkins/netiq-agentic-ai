"""Unit tests for Pydantic report schemas and validation rules."""

import pytest
from pydantic import ValidationError
from src.schemas.reports import (
    MetricItem,
    NonPaginatedMetricResult,
    ReportMode,
    ReportPage,
    ReportPagination,
    ReportSource,
    ReportStatus,
)


def make_valid_source() -> ReportSource:
    return ReportSource(
        apiId="test_api",
        reportCode="4g",
        endpoint="/api/nodes/reports/4g",
        mode=ReportMode.MOCK,
        contractStatus="UNVERIFIED",
    )


def test_valid_report_page():
    pagination = ReportPagination(
        page=0,
        size=50,
        returnedRecords=2,
        totalRecords=100,
        hasNext=True,
    )
    page = ReportPage(
        reportId="RAN_CELL_4G",
        domain="RAN",
        circle="BR",
        data=[{"cellId": "C1"}, {"cellId": "C2"}],
        pagination=pagination,
        source=make_valid_source(),
    )
    assert page.reportId == "RAN_CELL_4G"
    assert page.status == ReportStatus.SUCCESS
    assert len(page.data) == 2
    assert page.pagination.returnedRecords == 2


def test_returned_records_mismatch_raises():
    pagination = ReportPagination(
        page=0,
        size=50,
        returnedRecords=5,  # Contradicts len(data) == 1
        totalRecords=100,
        hasNext=True,
    )
    with pytest.raises(ValidationError, match="Contradictory pagination"):
        ReportPage(
            reportId="RAN_CELL_4G",
            domain="RAN",
            data=[{"cellId": "C1"}],
            pagination=pagination,
            source=make_valid_source(),
        )


def test_negative_total_records_raises():
    with pytest.raises(ValidationError):
        ReportPagination(
            page=0,
            size=50,
            returnedRecords=0,
            totalRecords=-10,
            hasNext=False,
        )


def test_negative_page_raises():
    with pytest.raises(ValidationError):
        ReportPagination(
            page=-1,
            size=50,
            returnedRecords=0,
            hasNext=False,
        )


def test_zero_or_negative_size_raises():
    with pytest.raises(ValidationError):
        ReportPagination(
            page=0,
            size=0,
            returnedRecords=0,
            hasNext=False,
        )


def test_empty_result_auto_classified_as_empty():
    pagination = ReportPagination(
        page=0,
        size=50,
        returnedRecords=0,
        totalRecords=0,
        hasNext=False,
    )
    page = ReportPage(
        reportId="RAN_CELL_4G",
        domain="RAN",
        data=[],
        pagination=pagination,
        source=make_valid_source(),
    )
    assert page.status == ReportStatus.EMPTY


def test_non_paginated_metric_result():
    metric = NonPaginatedMetricResult(
        reportId="STITCHING_SUMMARY",
        domain="Stitching",
        status=ReportStatus.SUCCESS,
        metrics=[MetricItem(label="Total Paths", value=150, unit="paths")],
        source=make_valid_source(),
    )
    assert len(metric.metrics) == 1
    assert metric.metrics[0].value == 150
