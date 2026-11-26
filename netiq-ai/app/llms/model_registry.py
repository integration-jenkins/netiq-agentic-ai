"""Model registry, identity expectations, and verification status schemas for NETIQ Agentic AI.

Architecture Role:
------------------
Maintains strict model identity contracts and verification statuses.
Guarantees:
1. No Misleading Aliases: Never maps a smaller or different-architecture model (e.g. qwen2.5:3b
   or nomic-embed-text) to appear as a different model family.
2. Explicit Verification Statuses: VERIFIED, IDENTITY_MISMATCH, MODEL_NOT_FOUND,
   UNAPPROVED_MODEL, CAPABILITY_MISMATCH, VERIFICATION_UNAVAILABLE.
3. Parameter & Architecture Parsing: Parses Ollama parameter strings ('4.0B', '596M', '137M')
   to enforce genuine physical model verification.
"""

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ModelVerificationStatus(str, Enum):
    """Strict physical identity verification states for local Ollama models."""
    VERIFIED = "VERIFIED"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    UNAPPROVED_MODEL = "UNAPPROVED_MODEL"
    CAPABILITY_MISMATCH = "CAPABILITY_MISMATCH"
    VERIFICATION_UNAVAILABLE = "VERIFICATION_UNAVAILABLE"


class ModelVerificationError(Exception):
    """Raised when a required model fails identity, capability, or availability verification."""

    def __init__(self, message: str, status: ModelVerificationStatus = ModelVerificationStatus.IDENTITY_MISMATCH) -> None:
        super().__init__(message)
        self.status = status


class ModelIdentityExpectation(BaseModel):
    """Expected physical identity contract for a configured model."""
    model_config = ConfigDict(frozen=True)

    tag: str
    expected_family: str | None = None
    expected_parameter_billions: float | None = None
    parameter_tolerance_billions: float = 0.6
    expected_quantization: str | None = None
    expected_capability: str | None = None
    expected_digest: str | None = None
    required: bool = True


class VerifiedModelRecord(BaseModel):
    """Actual inspected model identity and verification outcome."""
    model_config = ConfigDict(frozen=True)

    role: str
    configured_model_tag: str
    actual_model_tag: str | None = None
    expected_architecture: str | None = None
    detected_architecture: str | None = None
    expected_parameter_count: str | None = None
    detected_parameter_count: str | None = None
    quantization: str | None = None
    digest: str | None = None
    size_bytes: int | None = None
    capabilities: list[str] = Field(default_factory=list)
    embedding_dimensions: int | None = None
    status: ModelVerificationStatus
    available: bool = False
    required: bool = True
    last_verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mismatch_reason: str | None = None


class ModelCapability(BaseModel):
    """Specification of model limits, architecture, and verified runtime attributes."""
    model_config = ConfigDict(frozen=True)

    name: str
    display_name: str
    family: str
    parameter_size: str
    quantization: str = "Q4_K_M"
    context_length: int = 32768
    recommended_roles: list[str] = Field(default_factory=list)
    purpose: str = ""
    default_temperature: float = 0.0
    verified: bool = False
    digest: str | None = None


# Allowlist of approved model families for NETIQ Agentic AI
APPROVED_MODEL_FAMILIES = {"qwen3", "qwen3embed", "qwen2", "qwen"}

# Known approved genuine models (exact tags only; no cross-architecture aliases)
APPROVED_MODELS: dict[str, ModelCapability] = {
    "qwen3:4b-instruct-2507-q4_K_M": ModelCapability(
        name="qwen3:4b-instruct-2507-q4_K_M",
        display_name="Qwen3 4B Instruct 2507 (Q4_K_M)",
        family="qwen3",
        parameter_size="4.0B",
        quantization="Q4_K_M",
        context_length=32768,
        recommended_roles=["intent_classifier", "report_selector", "orchestrator_planner", "knowledge_agent"],
        purpose="Primary 4B Qwen3 Instruct model for classification, report matching, planning, and knowledge grounding.",
    ),
    "qwen3:4b-instruct-2507": ModelCapability(
        name="qwen3:4b-instruct-2507",
        display_name="Qwen3 4B Instruct 2507",
        family="qwen3",
        parameter_size="4.0B",
        quantization="Q4_K_M",
        context_length=32768,
        recommended_roles=["intent_classifier", "report_selector", "orchestrator_planner", "knowledge_agent"],
        purpose="Primary 4B Qwen3 Instruct model.",
    ),
    "qwen3-embedding:0.6b": ModelCapability(
        name="qwen3-embedding:0.6b",
        display_name="Qwen3 Embedding 0.6B",
        family="qwen3",
        parameter_size="0.6B",
        quantization="F16",
        context_length=8192,
        recommended_roles=["knowledge_retriever"],
        purpose="Genuine Qwen3 Embedding 0.6B model for multilingual semantic retrieval.",
    ),
    "qwen2.5-coder:7b": ModelCapability(
        name="qwen2.5-coder:7b",
        display_name="Qwen2.5-Coder 7B Instruct",
        family="qwen2",
        parameter_size="7.6B",
        quantization="Q4_K_M",
        context_length=32768,
        recommended_roles=["sql_agent"],
        purpose="SQL-focused model for validated Oracle 19c schema queries.",
    ),
}

# Only exact genuine display-name mappings (never map to a different architecture)
MODEL_ALIAS_MAP: dict[str, str] = {
    "qwen3 4b instruct 2507": "qwen3:4b-instruct-2507-q4_K_M",
    "qwen3:4b-instruct-2507-q4_k_m": "qwen3:4b-instruct-2507-q4_K_M",
    "qwen3:4b-instruct-2507": "qwen3:4b-instruct-2507",
    "qwen3 embedding 0.6b": "qwen3-embedding:0.6b",
    "qwen3-embedding:0.6b": "qwen3-embedding:0.6b",
    "qwen2.5-coder 7b": "qwen2.5-coder:7b",
    "qwen2.5-coder 7b instruct": "qwen2.5-coder:7b",
    "qwen2.5-coder 7b (optional)": "qwen2.5-coder:7b",
    "qwen2.5-coder:7b": "qwen2.5-coder:7b",
}


def normalize_model_name(name: str | None) -> str | None:
    """Normalize user-provided or display name into exact configured Ollama tag."""
    if not name:
        return None
    clean = name.strip().lower()
    return MODEL_ALIAS_MAP.get(clean, name.strip())


def parse_parameter_billions(param_str: str | None) -> float | None:
    """Parse Ollama parameter_size string (e.g. '4.0B', '596M', '137M', '7.6B') into billions."""
    if not param_str:
        return None
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([BMK])\s*$", str(param_str), re.IGNORECASE)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).upper()
    if unit == "B":
        return val
    if unit == "M":
        return val / 1000.0
    if unit == "K":
        return val / 1_000_000.0
    return None
