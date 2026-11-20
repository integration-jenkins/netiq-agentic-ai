"""Evidence and provenance schemas for deterministic tracing."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EvidenceType(str, Enum):
    REPORT_PAGE = "REPORT_PAGE"
    METRIC_SUMMARY = "METRIC_SUMMARY"
    CATALOG_METADATA = "CATALOG_METADATA"
    KNOWLEDGE_DOC = "KNOWLEDGE_DOC"


class EvidenceItem(BaseModel):
    """Traceable unit of source evidence backing an AI response."""
    model_config = ConfigDict(frozen=True)

    evidence_type: EvidenceType = EvidenceType.REPORT_PAGE
    report_id: str | None = None
    endpoint: str | None = None
    mode: str = "MOCK"
    record_count: int = 0
    sample_records: list[dict[str, Any]] = Field(default_factory=list)
    data_version: str | None = None
    data_as_of: str | None = None
    contract_status: str = "UNVERIFIED"
    citation: str | None = None


class EvidenceCollection(BaseModel):
    """Container for multi-source evidence."""
    model_config = ConfigDict(frozen=True)

    items: list[EvidenceItem] = Field(default_factory=list)
