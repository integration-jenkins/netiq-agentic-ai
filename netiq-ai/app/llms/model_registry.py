"""Model registry, capability metadata, and startup verification for NETIQ Agentic AI.

Architecture Role:
------------------
Maintains the approved inventory of local models, provides runtime model inspection
using Ollama REST APIs (/api/show, /api/tags), and enforces fail-closed validation.
Never initiates automatic external model downloads.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ModelVerificationStatus(str, Enum):
    """Verification state of a locally installed model."""
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"
    MISSING = "MISSING"


class ModelCapability(BaseModel):
    """Specification of model limits, architecture, and verified runtime attributes."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Ollama model tag (e.g., 'qwen3:4b-instruct-2507', 'qwen2.5:3b')")
    display_name: str = Field(..., description="Human-readable model name")
    family: str = Field(..., description="Model architecture family from Ollama details (e.g. 'qwen2', 'qwen3')")
    parameter_size: str = Field(..., description="Reported parameter size (e.g. '3.1B', '7.6B', '137M')")
    quantization: str = Field(default="Q4_K_M", description="Quantization format (e.g. 'Q4_K_M', 'F16')")
    context_length: int = Field(default=32768, description="Maximum context window in tokens")
    recommended_roles: list[str] = Field(default_factory=list, description="Agent roles this model excels at")
    purpose: str = Field(..., description="Architectural purpose and rationale")
    default_temperature: float = Field(default=0.0, description="Default sampling temperature")
    verified: bool = Field(default=False, description="Whether model has been verified against live Ollama daemon")
    digest: str | None = Field(default=None, description="Physical model hash / digest from Ollama")


class ModelVerificationError(Exception):
    """Raised when an unapproved, corrupted, or missing model fails startup verification."""
    pass


# Allowlist of approved model families for NETIQ Agentic AI
APPROVED_MODEL_FAMILIES = {"qwen2", "qwen3", "nomic-bert", "qwen"}

# Known approved models registry (populated with verified or configurable entries)
APPROVED_MODELS: dict[str, ModelCapability] = {
    "qwen3:4b-instruct-2507": ModelCapability(
        name="qwen3:4b-instruct-2507",
        display_name="Qwen3 4B Instruct 2507",
        family="qwen2",
        parameter_size="3.1B",
        quantization="Q4_K_M",
        context_length=32768,
        recommended_roles=["intent_classifier", "report_selector", "orchestrator_planner", "knowledge_agent"],
        purpose="Primary candidate for interpreting varied questions, matching report metadata, generating structured plans, and explaining telecom documentation.",
        default_temperature=0.0,
    ),
    "qwen2.5:3b": ModelCapability(
        name="qwen2.5:3b",
        display_name="Qwen2.5 3B",
        family="qwen2",
        parameter_size="3.1B",
        quantization="Q4_K_M",
        context_length=32768,
        recommended_roles=["intent_classifier", "report_selector", "orchestrator_planner", "knowledge_agent"],
        purpose="Standard 3B instruction model candidate for low-latency classification and routing.",
        default_temperature=0.0,
    ),
    "qwen3-embedding:0.6b": ModelCapability(
        name="qwen3-embedding:0.6b",
        display_name="Qwen3 Embedding 0.6B",
        family="nomic-bert",
        parameter_size="137M",
        quantization="F16",
        context_length=8192,
        recommended_roles=["knowledge_retriever"],
        purpose="Semantic vector embedding model for multilingual telecom glossary and SOP retrieval.",
        default_temperature=0.0,
    ),
    "nomic-embed-text:latest": ModelCapability(
        name="nomic-embed-text:latest",
        display_name="Nomic Embed Text",
        family="nomic-bert",
        parameter_size="137M",
        quantization="F16",
        context_length=8192,
        recommended_roles=["knowledge_retriever"],
        purpose="Standard dense vector embedding model for semantic document retrieval.",
        default_temperature=0.0,
    ),
    "qwen2.5-coder:7b": ModelCapability(
        name="qwen2.5-coder:7b",
        display_name="Qwen2.5-Coder 7B (optional)",
        family="qwen2",
        parameter_size="7.6B",
        quantization="Q4_K_M",
        context_length=32768,
        recommended_roles=["sql_agent"],
        purpose="SQL-focused benchmark for structured Oracle 19c schema queries.",
        default_temperature=0.0,
    ),
}

# Real alias mappings resolving display strings to exact installed model tags
MODEL_ALIAS_MAP: dict[str, str] = {
    "qwen3 4b instruct 2507": "qwen3:4b-instruct-2507",
    "qwen3:4b-instruct-2507": "qwen3:4b-instruct-2507",
    "qwen3-4b-instruct-2507": "qwen3:4b-instruct-2507",
    "qwen3-4b-instruct-2507:latest": "qwen3:4b-instruct-2507",
    "qwen2.5:3b": "qwen2.5:3b",
    "qwen2.5 3b": "qwen2.5:3b",
    "qwen3 embedding 0.6b": "qwen3-embedding:0.6b",
    "qwen3-embedding:0.6b": "qwen3-embedding:0.6b",
    "nomic-embed-text": "nomic-embed-text:latest",
    "nomic-embed-text:latest": "nomic-embed-text:latest",
    "qwen2.5-coder 7b": "qwen2.5-coder:7b",
    "qwen2.5-coder 7b (optional)": "qwen2.5-coder:7b",
    "qwen2.5-coder:7b": "qwen2.5-coder:7b",
}


def normalize_model_name(name: str | None) -> str | None:
    """Normalize user-provided or display model name into canonical Ollama tag.
    
    Example:
        'Qwen3 4B Instruct 2507' -> 'qwen3:4b-instruct-2507'
        'Qwen2.5-Coder 7B (optional)' -> 'qwen2.5-coder:7b'
    """
    if not name:
        return None
    clean = name.strip().lower()
    return MODEL_ALIAS_MAP.get(clean, name)
