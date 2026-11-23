"""Embedding model validation, actual vector length detection, and index compatibility guard.

Architecture Role:
------------------
Guarantees embedding integrity across semantic search and vector stores:
1. Dynamic Dimension Detection: Detects actual vector length via probe rather than guessing.
2. Strict Vector Validation: Rejects empty, NaN, Inf, all-zero, or dimension-mismatched vectors.
3. Index Compatibility Guard: Prevents mixing incompatible embedding dimensions in the same index.
4. Re-Index Notification: Identifies when embedding model changes necessitate index rebuilding.
"""

import math
from typing import Any
import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.settings.env import settings


class IncompatibleEmbeddingDimensionError(Exception):
    """Raised when an embedding vector does not match the active index dimension."""
    pass


class MalformedVectorError(Exception):
    """Raised when an embedding vector is empty, contains NaNs, or is corrupt."""
    pass


class EmbeddingMetadata(BaseModel):
    """Metadata tracking active embedding model physical attributes."""
    model_config = ConfigDict(frozen=True)

    model_tag: str
    detected_dimension: int
    architecture: str
    quantization: str
    version: str = "1.0"


class EmbeddingValidator:
    """Validates vector attributes, detects dimensional length, and prevents index corruption."""

    def __init__(self, expected_dimension: int = 768) -> None:
        self.expected_dimension = expected_dimension
        self._tracked_models: dict[str, EmbeddingMetadata] = {}

    def validate_vector(self, vector: list[float], expected_dim: int | None = None) -> list[float]:
        """Validate that a vector is non-empty, contains valid finite floats, and matches expected dimension.
        
        Raises:
            MalformedVectorError: If vector is empty, contains NaN or Inf, or is all zeros.
            IncompatibleEmbeddingDimensionError: If vector length does not match expected dimension.
        """
        if not vector or not isinstance(vector, (list, tuple)):
            raise MalformedVectorError("Embedding vector cannot be empty or non-sequence.")

        target_dim = expected_dim or self.expected_dimension
        if len(vector) != target_dim:
            raise IncompatibleEmbeddingDimensionError(
                f"Embedding dimension mismatch: Vector length {len(vector)} does not match expected {target_dim}. "
                "Re-indexing is required if embedding model was upgraded."
            )

        # Check for NaN, Inf, and non-zero
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
                    dim = len(vec)
                    self.expected_dimension = dim
                    return dim
            raise MalformedVectorError(
                f"Failed to detect embedding dimension from Ollama for model '{model_tag}': HTTP {resp.status_code}"
            )

    def check_index_compatibility(self, index_dimension: int, new_model_dimension: int) -> bool:
        """Verify whether an existing vector index is compatible with a new embedding model.
        
        Raises:
            IncompatibleEmbeddingDimensionError: If index dimension differs from new model dimension.
        """
        if index_dimension != new_model_dimension:
            raise IncompatibleEmbeddingDimensionError(
                f"Index incompatibility: Existing index has dimension {index_dimension}, "
                f"but new model produces dimension {new_model_dimension}. Full re-indexing required."
            )
        return True

    @staticmethod
    def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two validated vectors."""
        if len(vec1) != len(vec2):
            raise IncompatibleEmbeddingDimensionError(
                f"Cannot compute similarity between vectors of different lengths ({len(vec1)} vs {len(vec2)})."
            )
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a, b in zip(vec1, vec1)))
        norm2 = math.sqrt(sum(b * b for a, b in zip(vec2, vec2)))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot_product / (norm1 * norm2)


default_embedding_validator = EmbeddingValidator()
