"""Evidence and provenance schemas for deterministic tracing in NETIQ Agentic AI.

Architecture Role:
------------------
This module defines the evidence models used to ground AI responses in factual,
verifiable data. Every fact, count, or telecom table displayed to the user must be
accompanied by an `EvidenceItem` establishing its origin.

Key Guarantees:
---------------
1. Audit Traceability: Links every response directly to a specific backend report,
   API endpoint, and execution mode (MOCK vs LIVE).
2. Provenance Transparency: Clearly marks whether data was sourced from offline
   synthetic fixtures or live production telecom controllers.
3. Anti-Hallucination: Prevents the orchestrator from presenting synthetic data
   as verified real-world telecom evidence.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EvidenceType(str, Enum):
    """Categorized origin type for supporting evidence.
    
    - REPORT_PAGE: Tabular rows extracted from a standardized ReportPage.
    - METRIC_SUMMARY: Extracted numeric metric summary item.
    - CATALOG_METADATA: Structural column or filter definition from report metadata.
    - KNOWLEDGE_DOC: Curated telecom documentation or glossary citation.
    """
    REPORT_PAGE = "REPORT_PAGE"
    METRIC_SUMMARY = "METRIC_SUMMARY"
    CATALOG_METADATA = "CATALOG_METADATA"
    KNOWLEDGE_DOC = "KNOWLEDGE_DOC"


class EvidenceItem(BaseModel):
    """Traceable unit of source evidence backing an agent response.
    
    Attached to final chat payloads to enable users and audit systems to verify
    the exact query, endpoint, and dataset that produced an answer.
    """
    model_config = ConfigDict(frozen=True)

    evidence_type: EvidenceType = Field(default=EvidenceType.REPORT_PAGE, description="Classification of evidence origin")
    report_id: str | None = Field(default=None, description="Catalog report ID (e.g., 'RAN_CELL_4G')")
    endpoint: str | None = Field(default=None, description="Backend API path or endpoint invoked")
    mode: str = Field(default="MOCK", description="Execution mode provenance: 'MOCK' or 'LIVE'")
    record_count: int = Field(default=0, description="Total matching or returned records supporting this evidence")
    sample_records: list[dict[str, Any]] = Field(default_factory=list, description="Top sample rows proving factual backing")
    data_version: str | None = Field(default=None, description="Backend snapshot or ETL version identifier if provided")
    data_as_of: str | None = Field(default=None, description="Freshness timestamp of underlying telecom data")
    contract_status: str = Field(default="UNVERIFIED", description="Contract verification level ('UNVERIFIED' vs 'VERIFIED')")
    citation: str | None = Field(default=None, description="Human-readable citation string displayed in UI")


class EvidenceCollection(BaseModel):
    """Container for aggregating multi-source evidence across multiple retrieval steps."""
    model_config = ConfigDict(frozen=True)

    items: list[EvidenceItem] = Field(default_factory=list, description="Collection of individual evidence records")
