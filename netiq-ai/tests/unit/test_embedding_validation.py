"""Unit tests for embedding model verification, dimensional checks, and index guards."""

import math
import pytest
from app.llms.embedding_validator import (
    EmbeddingValidator,
    IncompatibleEmbeddingDimensionError,
    MalformedVectorError,
)


def test_valid_768_dimension_vector_passes():
    """A valid 768-dimensional float vector passes validation."""
    validator = EmbeddingValidator(expected_dimension=768)
    valid_vec = [0.01 * (i % 10) for i in range(768)]
    valid_vec[0] = 0.5  # Ensure not all-zero

    result = validator.validate_vector(valid_vec)
    assert len(result) == 768


def test_incompatible_dimension_raises():
    """Passing a 512-dim vector when 768 is expected raises IncompatibleEmbeddingDimensionError."""
    validator = EmbeddingValidator(expected_dimension=768)
    wrong_vec = [0.1] * 512

    with pytest.raises(IncompatibleEmbeddingDimensionError, match="Vector length 512 does not match expected 768"):
        validator.validate_vector(wrong_vec)


def test_empty_vector_raises_malformed():
    """Empty list or non-sequence raises MalformedVectorError."""
    validator = EmbeddingValidator(expected_dimension=768)

    with pytest.raises(MalformedVectorError, match="cannot be empty"):
        validator.validate_vector([])


def test_nan_or_inf_in_vector_raises_malformed():
    """Vectors containing NaN or Infinity must be rejected."""
    validator = EmbeddingValidator(expected_dimension=768)
    nan_vec = [0.1] * 768
    nan_vec[10] = float("nan")

    with pytest.raises(MalformedVectorError, match="contains NaN or infinite"):
        validator.validate_vector(nan_vec)

    inf_vec = [0.1] * 768
    inf_vec[20] = float("inf")

    with pytest.raises(MalformedVectorError, match="contains NaN or infinite"):
        validator.validate_vector(inf_vec)


def test_all_zero_vector_raises_malformed():
    """Vectors where every float is 0.0 must be rejected."""
    validator = EmbeddingValidator(expected_dimension=768)
    zero_vec = [0.0] * 768

    with pytest.raises(MalformedVectorError, match="completely zeroed out"):
        validator.validate_vector(zero_vec)


def test_index_compatibility_guard():
    """Switching embedding dimension from 768 to 1536 raises error requiring re-indexing."""
    validator = EmbeddingValidator()
    with pytest.raises(IncompatibleEmbeddingDimensionError, match="Full re-indexing required"):
        validator.check_index_compatibility(index_dimension=768, new_model_dimension=1536)

    # Identical dimension passes
    assert validator.check_index_compatibility(index_dimension=768, new_model_dimension=768) is True


def test_cosine_similarity_computation():
    """Verifies standard cosine similarity between telecom term embeddings."""
    validator = EmbeddingValidator()
    # Identical vectors
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert math.isclose(validator.cosine_similarity(v1, v2), 1.0)

    # Orthogonal vectors
    v3 = [0.0, 1.0, 0.0]
    assert math.isclose(validator.cosine_similarity(v1, v3), 0.0)

    # Opposing vectors
    v4 = [-1.0, 0.0, 0.0]
    assert math.isclose(validator.cosine_similarity(v1, v4), -1.0)
