"""Unit tests for Orchestration Planner and structured plan validation."""

import pytest
from app.orchestrator.planner import (
    OrchestrationPlanner,
    PlanValidationError,
    default_orchestration_planner,
)
from src.schemas.execution_plan import ExecutionPlan, ExecutionStep
from src.schemas.user import UserContext
from src.security.circle_access import UnauthorizedCircleError


def test_valid_structured_plan_validation():
    """A well-formed plan with approved tools, verified reports, and valid dependencies passes."""
    planner = OrchestrationPlanner()
    plan = ExecutionPlan(
        plan_id="plan-001",
        intent="NETWORK_IMPACT_ANALYSIS",
        circle="BR",
        steps=[
            ExecutionStep(
                step_id="step_1",
                tool="report_retrieval",
                report_id="RAN_CELL_4G",
                parameters={"circle": "BR"},
                depends_on=[],
            ),
            ExecutionStep(
                step_id="step_2",
                tool="report_retrieval",
                report_id="MW_TRANSMISSION_LINK_INVENTORY",
                parameters={"circle": "BR"},
                depends_on=["step_1"],
            ),
        ],
    )
    validated = planner.validate_plan(plan)
    assert validated.validated is True
    assert len(validated.steps) == 2


def test_unapproved_tool_rejected():
    """Referencing an unapproved tool must raise PlanValidationError."""
    planner = OrchestrationPlanner()
    plan = ExecutionPlan(
        plan_id="plan-bad-tool",
        intent="REPORT_QUERY",
        steps=[
            ExecutionStep(
                step_id="step_1",
                tool="arbitrary_unapproved_scraper",
                parameters={},
            )
        ],
    )
    with pytest.raises(PlanValidationError, match="references unapproved tool"):
        planner.validate_plan(plan)


def test_unverified_report_id_rejected():
    """Referencing a report ID not in catalog.yaml must be rejected."""
    planner = OrchestrationPlanner()
    plan = ExecutionPlan(
        plan_id="plan-fake-report",
        intent="REPORT_QUERY",
        steps=[
            ExecutionStep(
                step_id="step_1",
                tool="report_retrieval",
                report_id="FABRICATED_REPORT_ID_999",
                parameters={},
            )
        ],
    )
    with pytest.raises(PlanValidationError, match="references unverified report_id"):
        planner.validate_plan(plan)


def test_circular_dependency_rejected():
    """Circular dependencies must be caught and rejected."""
    planner = OrchestrationPlanner()
    plan = ExecutionPlan(
        plan_id="plan-circular",
        intent="REPORT_QUERY",
        steps=[
            ExecutionStep(
                step_id="step_1",
                tool="report_retrieval",
                report_id="RAN_CELL_4G",
                depends_on=["step_1"],  # depends on itself
            )
        ],
    )
    with pytest.raises(PlanValidationError, match="Circular dependency"):
        planner.validate_plan(plan)


def test_invalid_forward_dependency_rejected():
    """Depending on a step not yet executed must be rejected."""
    planner = OrchestrationPlanner()
    plan = ExecutionPlan(
        plan_id="plan-forward-dep",
        intent="REPORT_QUERY",
        steps=[
            ExecutionStep(
                step_id="step_1",
                tool="report_retrieval",
                report_id="RAN_CELL_4G",
                depends_on=["step_2"],  # step_2 is not defined before step_1
            ),
            ExecutionStep(
                step_id="step_2",
                tool="report_retrieval",
                report_id="MW_UBR_NODE_INVENTORY",
                depends_on=[],
            ),
        ],
    )
    with pytest.raises(PlanValidationError, match="is not defined before it"):
        planner.validate_plan(plan)


def test_exceeding_max_steps_rejected():
    """Plans with more than 5 steps must be rejected."""
    planner = OrchestrationPlanner()
    steps = [
        ExecutionStep(
            step_id=f"step_{i}",
            tool="knowledge_retrieval",
            parameters={"q": f"test_{i}"},
        )
        for i in range(1, 7)  # 6 steps
    ]
    with pytest.raises(Exception):  # Pydantic or planner validation
        plan = ExecutionPlan(
            plan_id="plan-too-many-steps",
            intent="REPORT_QUERY",
            steps=steps,
        )
        planner.validate_plan(plan)


def test_user_circle_authorization_enforced_in_plan():
    """User without access to plan's circle must be blocked."""
    planner = OrchestrationPlanner()
    user = UserContext(
        username="delhi_analyst",
        roles=["analyst"],
        permitted_circles=["DL"],
        is_admin=False,
    )
    plan = ExecutionPlan(
        plan_id="plan-circle-violation",
        intent="REPORT_QUERY",
        circle="BR",  # Bihar circle
        steps=[
            ExecutionStep(
                step_id="step_1",
                tool="report_retrieval",
                report_id="RAN_CELL_4G",
                parameters={"circle": "BR"},
            )
        ],
    )
    with pytest.raises(UnauthorizedCircleError, match="not authorized to access circle 'BR'"):
        planner.validate_plan(plan, user=user)
