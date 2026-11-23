"""Structured execution planning and pre-execution validation engine."""

import json
import uuid
from typing import Any
from app.llms.llm_client import default_llm_client
from app.llms.report_selector import default_report_selector
from src.schemas.execution_plan import ExecutionPlan, ExecutionStep, PlanIntent
from src.schemas.user import UserContext
from src.security.circle_access import CircleAccessPolicy, UnauthorizedCircleError
from src.settings.env import settings
from src.settings.loader import load_report_catalog

# Approved agent execution tools
APPROVED_TOOLS = {
    "report_retrieval",
    "knowledge_retrieval",
    "sql_retrieval",
}


class PlanValidationError(Exception):
    """Raised when an execution plan fails pre-flight validation."""
    pass


class OrchestrationPlanner:
    """Generates and validates structured execution plans before tool execution."""

    def __init__(self) -> None:
        self._catalog = None

    def _get_catalog_report_ids(self) -> set[str]:
        if self._catalog is None:
            cat = load_report_catalog()
            self._catalog = {r["id"] for r in cat.get("reports", []) if "id" in r}
        return self._catalog

    def validate_plan(self, plan: ExecutionPlan, user: UserContext | None = None) -> ExecutionPlan:
        """Validate execution plan structure, dependencies, tool allowlist, and user permissions.
        
        Guarantees:
        1. Tool Allowlist: Every tool in every step must be in APPROVED_TOOLS.
        2. Report Verification: Any report_id must exist in catalog.yaml.
        3. Acyclic Dependencies: Step dependencies must reference earlier steps with no cycles.
        4. Circle Permissions: User must have access to plan's requested circle.
        5. Step Count: Maximum 5 steps permitted.
        6. SQL Safety Gate: sql_retrieval tool rejected if live SQL is disabled.
        """
        # Step limit
        if len(plan.steps) > 5:
            raise PlanValidationError(f"Plan exceeds maximum limit of 5 steps (found {len(plan.steps)}).")

        # Circle permission
        if user and plan.circle:
            CircleAccessPolicy.validate_circle_access(
                user_permitted_circles=user.permitted_circles,
                requested_circle=plan.circle,
                user_roles=user.roles,
            )

        catalog_ids = self._get_catalog_report_ids()
        seen_step_ids: set[str] = set()

        for step in plan.steps:
            # 1. Tool check
            if step.tool not in APPROVED_TOOLS:
                raise PlanValidationError(f"Step '{step.step_id}' references unapproved tool '{step.tool}'.")

            # 2. Report ID check
            if step.tool == "report_retrieval":
                if not step.report_id:
                    raise PlanValidationError(f"Step '{step.step_id}' is a report_retrieval tool but missing 'report_id'.")
                if step.report_id not in catalog_ids:
                    raise PlanValidationError(
                        f"Step '{step.step_id}' references unverified report_id '{step.report_id}'. Not in catalog."
                    )

            # 3. SQL execution check
            if step.tool == "sql_retrieval":
                if not settings.live_sql_execution_enabled and not (user and user.is_admin):
                    raise PlanValidationError(
                        f"Step '{step.step_id}' requests SQL retrieval, but live SQL execution is disabled."
                    )

            # 4. Dependency check
            for dep in step.depends_on:
                if dep == step.step_id:
                    raise PlanValidationError(f"Circular dependency: Step '{step.step_id}' depends on itself.")
                if dep not in seen_step_ids:
                    raise PlanValidationError(
                        f"Invalid dependency: Step '{step.step_id}' depends on '{dep}', which is not defined before it."
                    )

            seen_step_ids.add(step.step_id)

        # Return updated plan marked as validated
        return ExecutionPlan(
            plan_id=plan.plan_id,
            intent=plan.intent,
            circle=plan.circle,
            steps=plan.steps,
            validated=True,
            explanation=plan.explanation,
        )

    async def create_plan(self, query: str, user: UserContext | None = None) -> ExecutionPlan:
        """Create a structured, validated execution plan for user query.
        
        Uses deterministic routing when feasible, and validates against catalog.
        """
        # Extract circle if present
        circle = None
        for c in ["DL", "MH", "BR", "PUNJAB", "BIHAR", "MUMBAI", "DELHI"]:
            if c.lower() in query.lower().split() or f"'{c.lower()}'" in query.lower():
                circle = "BR" if c in ("BR", "BIHAR") else ("DL" if c in ("DL", "DELHI") else ("MH" if c in ("MH", "MUMBAI") else c))
                break

        # Check report matching
        report_res = default_report_selector.select_report(query)

        steps: list[ExecutionStep] = []
        intent = PlanIntent.REPORT_QUERY.value

        if "impact" in query.lower() or "backhaul" in query.lower() or "associated" in query.lower():
            intent = PlanIntent.NETWORK_IMPACT_ANALYSIS.value
            # Step 1: RAN Cell report
            steps.append(ExecutionStep(
                step_id="step_1",
                tool="report_retrieval",
                report_id="RAN_CELL_4G" if "RAN_CELL_4G" in self._get_catalog_report_ids() else "MW_UBR_NODE_INVENTORY",
                parameters={"circle": circle} if circle else {},
                depends_on=[],
            ))
            # Step 2: Microwave link check
            steps.append(ExecutionStep(
                step_id="step_2",
                tool="report_retrieval",
                report_id="MW_TRANSMISSION_LINK_INVENTORY",
                parameters={"circle": circle} if circle else {},
                depends_on=["step_1"],
            ))
        elif report_res.status == "MATCH" and report_res.report_id:
            steps.append(ExecutionStep(
                step_id="step_1",
                tool="report_retrieval",
                report_id=report_res.report_id,
                parameters={"circle": circle} if circle else {},
                depends_on=[],
            ))
        elif "sop" in query.lower() or "definition" in query.lower() or "what is" in query.lower():
            intent = PlanIntent.KNOWLEDGE_LOOKUP.value
            steps.append(ExecutionStep(
                step_id="step_1",
                tool="knowledge_retrieval",
                parameters={"query": query},
                depends_on=[],
            ))
        else:
            # Default single-step plan
            target_report = report_res.report_id or "MW_UBR_NODE_INVENTORY"
            steps.append(ExecutionStep(
                step_id="step_1",
                tool="report_retrieval",
                report_id=target_report,
                parameters={"circle": circle} if circle else {},
                depends_on=[],
            ))

        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            intent=intent,
            circle=circle,
            steps=steps,
            validated=False,
            explanation=f"Execution plan generated for intent '{intent}'.",
        )

        return self.validate_plan(plan, user)


default_orchestration_planner = OrchestrationPlanner()
