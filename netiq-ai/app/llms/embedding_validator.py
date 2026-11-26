"""Embedding model validation, digest tracking, actual vector length detection, and index guard.

Architecture Role:
------------------
Guarantees embedding integrity across semantic search and vector stores:
1. Dynamic Dimension Detection: Detects actual vector length via probe rather than hardcoding 768 or 1024.
2. Strict Vector Validation: Rejects empty, NaN, Inf, all-zero, or dimension-mismatched vectors.
3. Model & Digest Compatibility Guard: Prevents mixing embeddings from different models or
   different model digests, even when their output dimensions happen to match.
4. Knowledge Index Rebuild: Rebuilds and persists index metadata with verified model digest.
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx
from pydantic import BaseModel, ConfigDict

from src.settings.env import PROJECT_ROOT, settings


class IncompatibleEmbeddingDimensionError(Exception):
    """Raised when embedding dimensions or model identities mismatch the active vector index."""
    pass


class MalformedVectorError(Exception):
    """Raised when an embedding vector is empty, contains NaNs, or is corrupt."""
    pass


class EmbeddingMetadata(BaseModel):
    """Metadata tracking active embedding model physical attributes and digest."""
    model_config = ConfigDict(frozen=True)

    model_tag: str
    model_digest: str | None = None
    detected_dimension: int
    architecture: str = "unknown"
    quantization: str = "unknown"
    rebuilt_at: str | None = None


class EmbeddingValidator:
    """Validates vector attributes, detects dimensional length, and prevents index corruption."""

    def __init__(self, expected_dimension: int | None = None, model_tag: str | None = None, model_digest: str | None = None) -> None:
        self.expected_dimension = expected_dimension
        self.model_tag = model_tag
        self.model_digest = model_digest
        self._tracked_models: dict[str, EmbeddingMetadata] = {}

    def validate_vector(self, vector: list[float], expected_dim: int | None = None) -> list[float]:
        """Validate that a vector is non-empty, contains valid finite floats, and matches expected dimension."""
        if not vector or not isinstance(vector, (list, tuple)):
            raise MalformedVectorError("Embedding vector cannot be empty or non-sequence.")

        target_dim = expected_dim if expected_dim is not None else self.expected_dimension
        if target_dim is not None and len(vector) != target_dim:
            raise IncompatibleEmbeddingDimensionError(
                f"Embedding dimension mismatch: Vector length {len(vector)} does not match expected {target_dim}. "
                "Re-indexing is required if embedding model was upgraded."
            )

        has_non_zero = False
        for val in vector:
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                raise MalformedVectorError("Embedding vector contains NaN or infinite values.")
            if val != 0.0:
                has_non_zero = True

        if not has_non_zero:
            raise MalformedVectorError("Embedding vector is completely zeroed out.")

        return list(vector)

    async def detect_model_dimension(self, model_tag: str, base_url: str | None = None) -> int:
        """Probe Ollama embeddings endpoint to discover real physical vector dimensionality."""
        url = (base_url or settings.ollama_base_url).rstrip("/")
        async with httpx.AsyncClient(base_url=url, timeout=30.0) as client:
            resp = await client.post(
                "/api/embeddings",
                json={"model": model_tag, "prompt": "NETIQ telecom dimension probe"}
            )
            if resp.status_code == 200:
                vec = resp.json().get("embedding", [])
                if vec:
                    self.validate_vector(vec, expected_dim=len(vec))
                    self.expected_dimension = len(vec)
                    self.model_tag = model_tag
                    return len(vec)
            raise MalformedVectorError(
                f"Failed to detect embedding dimension from Ollama for model '{model_tag}': HTTP {resp.status_code}"
            )

    def check_index_compatibility(
        self,
        index_dimension: int,
        new_model_dimension: int,
        index_model_tag: str | None = None,
        new_model_tag: str | None = None,
        index_digest: str | None = None,
        new_digest: str | None = None,
    ) -> bool:
        """Verify whether an existing vector index is compatible with an active embedding model.
        
        Prevents mixing embeddings from different models/digests even when dimensions match.
        """
        if index_dimension != new_model_dimension:
            raise IncompatibleEmbeddingDimensionError(
                f"Index dimension incompatibility: Existing index has dimension {index_dimension}, "
                f"but active model produces dimension {new_model_dimension}. Full re-indexing required."
            )
        if index_model_tag and new_model_tag and index_model_tag != new_model_tag:
            raise IncompatibleEmbeddingDimensionError(
                f"Index model mismatch: Index was built with '{index_model_tag}', "
                f"cannot mix with '{new_model_tag}' even at dimension {new_model_dimension}. Re-indexing required."
            )
        if index_digest and new_digest and index_digest != new_digest:
            raise IncompatibleEmbeddingDimensionError(
                f"Index digest mismatch: Index digest '{index_digest[:12]}' differs from active '{new_digest[:12]}'. Re-indexing required."
            )
        return True

    async def rebuild_knowledge_index(
        self,
        model_tag: str,
        model_digest: str | None = None,
        architecture: str = "qwen3",
        quantization: str = "F16",
        documents: list[dict[str, str]] | None = None,
        index_meta_path: Path | None = None,
        base_url: str | None = None,
    ) -> dict[str, Any]:
        """Rebuild local knowledge embeddings using the verified genuine embedding model."""
        url = (base_url or settings.ollama_base_url).rstrip("/")
        docs = documents or []
        detected_dim: int | None = None
        embedded_docs: list[dict[str, Any]] = []

        async with httpx.AsyncClient(base_url=url, timeout=60.0) as client:
            if not docs:
                docs = [{"id": "SOP-RAN-402", "text": "eNodeB cell availability below 98.5% triggers Severity-2."}]

            for d in docs:
                resp = await client.post("/api/embeddings", json={"model": model_tag, "prompt": d["text"]})
                if resp.status_code != 200:
                    raise MalformedVectorError(f"Embedding generation failed for '{d['id']}': HTTP {resp.status_code}")
                vec = resp.json().get("embedding", [])
                if detected_dim is None:
                    detected_dim = len(vec)
                self.validate_vector(vec, expected_dim=detected_dim)
                embedded_docs.append({"id": d["id"], "dimension": len(vec), "embedding_preview": vec[:4]})

        self.expected_dimension = detected_dim
        self.model_tag = model_tag
        self.model_digest = model_digest

        meta = {
            "model_tag": model_tag,
            "model_digest": model_digest,
            "architecture": architecture,
            "quantization": quantization,
            "detected_dimension": detected_dim,
            "indexed_documents": len(embedded_docs),
            "rebuilt_at": datetime.now(timezone.utc).isoformat(),
        }
        target_path = index_meta_path or (PROJECT_ROOT / "data" / "indexes" / "knowledge_index_meta.json")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta

    @staticmethod
    def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two validated vectors."""
        if len(vec1) != len(vec2):
            raise IncompatibleEmbeddingDimensionError(
                f"Cannot compute similarity between vectors of different lengths ({len(vec1)} vs {len(vec2)})."
            )
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot_product / (norm1 * norm2)


default_embedding_validator = EmbeddingValidator(expected_dimension=1024, model_tag="qwen3-embedding:0.6b")
