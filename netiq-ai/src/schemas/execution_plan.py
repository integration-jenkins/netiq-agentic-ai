"""Strict Pydantic v2 schemas for structured, executable agent plans."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class PlanIntent(str, Enum):
    """Supported high-level execution plan intents."""
    REPORT_QUERY = "REPORT_QUERY"
    NETWORK_IMPACT_ANALYSIS = "NETWORK_IMPACT_ANALYSIS"
    CORRELATION_ANALYSIS = "CORRELATION_ANALYSIS"
    KNOWLEDGE_LOOKUP = "KNOWLEDGE_LOOKUP"
    SQL_ANALYTICS = "SQL_ANALYTICS"


class ExecutionStep(BaseModel):
    """Discrete, deterministic execution step within a plan."""
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(..., description="Unique step identifier within plan (e.g. 'step_1')")
    tool: str = Field(..., description="Target tool name ('report_retrieval', 'knowledge_retrieval', 'sql_retrieval')")
    report_id: str | None = Field(default=None, description="Approved NETIQ report ID if tool is report_retrieval")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Typed parameters passed to tool")
    depends_on: list[str] = Field(default_factory=list, description="List of prior step_ids this step depends on")


class ExecutionPlan(BaseModel):
    """Structured, validated plan ready for deterministic execution."""
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(..., description="Unique UUID for this plan")
    intent: str = Field(..., description="Classified intent (e.g. 'NETWORK_IMPACT_ANALYSIS')")
    circle: str | None = Field(default=None, description="Target telecom circle (e.g. 'BR', 'DL')")
    steps: list[ExecutionStep] = Field(..., min_length=1, max_length=5, description="Ordered execution steps")
    validated: bool = Field(default=False, description="Whether plan passed pre-execution policy checks")
    explanation: str = Field(default="", description="Human-readable rationale for the selected plan")
