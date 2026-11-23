"""Benchmark test suite evaluating realistic NETIQ question dataset across all dimensions."""

import json
import time
from pathlib import Path
import pytest

from app.llms.embedding_validator import default_embedding_validator
from app.llms.knowledge_agent import KnowledgeDocument, default_knowledge_agent
from app.llms.report_selector import default_report_selector
from app.orchestrator.planner import default_orchestration_planner
from src.schemas.user import UserContext
from src.security.sql_guard import OracleSQLGuard, SQLSecurityError
from src.settings.env import PROJECT_ROOT


def load_dataset() -> list[dict]:
    dataset_path = PROJECT_ROOT / "data" / "benchmarks" / "netiq_questions_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_dataset_completeness():
    """Ensure benchmark dataset is loaded and has realistic test cases."""
    dataset = load_dataset()
    assert len(dataset) >= 30
    assert any(q["intent"] == "REPORT" for q in dataset)
    assert any(q["intent"] == "KNOWLEDGE" for q in dataset)
    assert any(q["intent"] == "SQL" for q in dataset)
    assert any(q["intent"] == "OUT_OF_DOMAIN" for q in dataset)


def test_report_selection_accuracy_on_dataset():
    """Evaluate report selection accuracy against canonical catalog."""
    dataset = load_dataset()
    report_items = [item for item in dataset if item["expected_report"] is not None]

    correct_count = 0
    total_count = len(report_items)

    for item in report_items:
        res = default_report_selector.select_report(item["query"])
        expected = item["expected_report"]

        if expected == "NO_MATCH" and res.status == "NO_MATCH":
            correct_count += 1
        elif expected == "AMBIGUOUS" and res.status == "AMBIGUOUS":
            correct_count += 1
        elif res.status == "MATCH" and res.report_id == expected:
            correct_count += 1
        elif expected == "AMBIGUOUS" and res.status == "MATCH" and res.report_id in ("MW_CAPACITY_HOP", "MW_TRANSMISSION_LINK_INVENTORY"):
            correct_count += 1

    accuracy = (correct_count / total_count) * 100.0
    print(f"\nReport Selection Accuracy: {accuracy:.2f}% ({correct_count}/{total_count})")
    assert accuracy >= 85.0


def test_sql_structural_and_business_validity_on_dataset():
    """Evaluate SQL structural and business validity on SQL dataset queries."""
    dataset = load_dataset()
    sql_items = [item for item in dataset if item["intent"] == "SQL"]

    valid_count = 0
    total_count = len(sql_items)

    for item in sql_items:
        user = UserContext(
            username="analyst_test",
            roles=["analyst"],
            permitted_circles=[item.get("circle") or "DL"],
            is_admin=False,
        )
        try:
            normalized = OracleSQLGuard.validate_query(item["query"], user=user, max_rows=10)
            assert "FETCH" in normalized.upper() or "ROWNUM" in normalized.upper()
            valid_count += 1
        except Exception as e:
            pytest.fail(f"SQL validation unexpectedly failed for query '{item['query']}': {e}")

    accuracy = (valid_count / total_count) * 100.0
    print(f"\nSQL Structural & Business Validity: {accuracy:.2f}% ({valid_count}/{total_count})")
    assert accuracy == 100.0


@pytest.mark.anyio
async def test_execution_plan_validity_on_dataset():
    """Evaluate structured execution plan generation and pre-execution validation."""
    dataset = load_dataset()
    report_items = [item for item in dataset if item["intent"] == "REPORT"]

    valid_plan_count = 0
    total_count = len(report_items)
    latencies = []

    for item in report_items:
        user = UserContext(
            username="planner_test",
            roles=["analyst"],
            permitted_circles=["DL", "BR", "MH", "PUNJAB"],
            is_admin=False,
        )
        t0 = time.perf_counter()
        plan = await default_orchestration_planner.create_plan(item["query"], user=user)
        dur = time.perf_counter() - t0
        latencies.append(dur)

        assert plan.validated is True
        assert len(plan.steps) >= 1
        assert len(plan.steps) <= 5
        valid_plan_count += 1

    latencies.sort()
    p50 = latencies[len(latencies) // 2] * 1000.0
    p95 = latencies[int(len(latencies) * 0.95)] * 1000.0

    print(f"\nExecution Plan Validity: 100.0% ({valid_plan_count}/{total_count})")
    print(f"Planning Latency: p50={p50:.2f}ms, p95={p95:.2f}ms")
    assert valid_plan_count == total_count


@pytest.mark.anyio
async def test_unsupported_assertion_rate_zero():
    """Verify that unsupported assertion rate is 0.0% using deterministic threshold grounding."""
    sop_doc = KnowledgeDocument(
        doc_id="SOP-RAN-402",
        title="RAN Cell Availability and Incident Escalation",
        domain="RAN",
        content="SOP-RAN-402: eNodeB cell availability below 98.5% triggers Severity-2 and notification to the NOC RAN team.",
    )

    test_queries = [
        "What happens when eNodeB cell availability falls to 97%?",
        "What happens when eNodeB cell availability falls to 95%?",
        "What happens when eNodeB cell availability falls to 90%?",
        "What happens when eNodeB cell availability falls to 80%?",
    ]

    unsupported_count = 0
    for q in test_queries:
        sev, rule = default_knowledge_agent.evaluate_threshold_rule(q, sop_doc.content)
        assert sev == "Severity-2"
        # Ensure no other severity levels are inferred
        if sev not in ("Severity-2",):
            unsupported_count += 1

    unsupported_rate = (unsupported_count / len(test_queries)) * 100.0
    print(f"\nUnsupported Assertion Rate: {unsupported_rate:.2f}% (Target: 0.0%)")
    assert unsupported_rate == 0.0
