"""Unit tests for Report Selector against canonical metadata catalog."""

import pytest
from app.llms.report_selector import ReportSelector, default_report_selector


def test_mandatory_microwave_hop_degradation_does_not_select_node_inventory():
    """Mandatory Test:
    Question: 'List microwave hop link degradations and capacity for Mumbai.'
    Expected:
    - Identify verified MW transmission-link or hop-level reports (MW_CAPACITY_HOP, MW_TRANSMISSION_LINK_INVENTORY)
      or return AMBIGUOUS.
    - NEVER select MW_UBR_NODE_INVENTORY or MW_NODE_INVENTORY.
    """
    selector = ReportSelector()
    res = selector.select_report("List microwave hop link degradations and capacity for Mumbai.")

    # Must be AMBIGUOUS between hop/link reports or MATCH one of them, but NEVER node inventory
    assert res.report_id != "MW_UBR_NODE_INVENTORY"
    assert res.report_id != "MW_NODE_INVENTORY"
    if res.status == "AMBIGUOUS":
        assert any("HOP" in c or "LINK" in c or "CAPACITY" in c for c in res.candidate_ids)
    elif res.status == "MATCH":
        assert res.report_id in ("MW_CAPACITY_HOP", "MW_TRANSMISSION_LINK_INVENTORY")


def test_deterministic_exact_match_ran_cell():
    """Query explicitly for 4G cells matches RAN_CELL_4G."""
    selector = ReportSelector()
    res = selector.select_report("Show me 4G cell inventory and status for Delhi.")
    assert res.status == "MATCH"
    assert res.report_id == "RAN_CELL_4G"
    assert res.domain == "RAN"


def test_out_of_domain_query_returns_no_match():
    """Queries for non-telecom topics must return NO_MATCH."""
    selector = ReportSelector()
    queries = [
        "What is the salary of software engineers in Google?",
        "Show current weather forecast for Bangalore.",
        "Employee health insurance policy document.",
    ]
    for q in queries:
        res = selector.select_report(q)
        assert res.status == "NO_MATCH"
        assert res.report_id is None


def test_selected_report_id_exists_in_catalog():
    """Every selected report ID must strictly exist in the catalog."""
    selector = ReportSelector()
    catalog = selector._get_catalog()

    test_queries = [
        "Show 4G cells for Bihar",
        "Microwave site inventory report",
        "Wireline node inventory",
        "AI baseline audit",
    ]
    for q in test_queries:
        res = selector.select_report(q)
        if res.status == "MATCH":
            assert res.report_id in catalog
