"""Comprehensive unit tests for strict physical LLM & embedding model identity validation."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.llms.embedding_validator import (
    EmbeddingValidator,
    IncompatibleEmbeddingDimensionError,
)
from app.llms.llm_client import LLMClient
from app.llms.model_manager import ModelManager
from app.llms.model_registry import (
    ModelIdentityExpectation,
    ModelVerificationError,
    ModelVerificationStatus,
)
from src.adapters.llm.provider import OllamaProvider
from src.api.app import create_app


def _make_mock_ollama(tags_list: list[dict], show_map: dict[str, dict]):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": tags_list})
        if request.url.path == "/api/show":
            import json
            name = json.loads(request.content.decode("utf-8")).get("name")
            if name in show_map:
                return httpx.Response(200, json=show_map[name])
            return httpx.Response(404, json={"error": f"model '{name}' not found"})
        if request.url.path == "/api/generate":
            return httpx.Response(200, json={"response": "OK", "done": True, "eval_count": 1, "eval_duration": 10000000})
        return httpx.Response(404)
    return httpx.MockTransport(handler)


@pytest.mark.anyio
async def test_genuine_qwen3_4b_acceptance():
    transport = _make_mock_ollama(
        tags_list=[{"name": "qwen3:4b-instruct-2507-q4_K_M", "digest": "0edcdef34593", "size": 2500000000}],
        show_map={
            "qwen3:4b-instruct-2507-q4_K_M": {
                "details": {"family": "qwen3", "parameter_size": "4.0B", "quantization_level": "Q4_K_M"},
                "capabilities": ["completion", "tools"],
            }
        },
    )
    mgr = ModelManager(provider=OllamaProvider(transport=transport))
    rec = await mgr.verify_model_identity(
        role="intent_classifier",
        expectation=ModelIdentityExpectation(
            tag="qwen3:4b-instruct-2507-q4_K_M",
            expected_family="qwen3",
            expected_parameter_billions=4.0,
            expected_quantization="Q4_K_M",
            expected_capability="completion",
        ),
    )
    assert rec.status == ModelVerificationStatus.VERIFIED
    assert rec.available is True
    assert rec.detected_architecture == "qwen3"


@pytest.mark.anyio
async def test_incorrectly_aliased_qwen25_3b_rejected():
    """A Qwen2 3.1B model pretending to be Qwen3 4B must fail with IDENTITY_MISMATCH."""
    transport = _make_mock_ollama(
        tags_list=[{"name": "qwen3:4b-instruct-2507", "digest": "357c53fb659c", "size": 1929912432}],
        show_map={
            "qwen3:4b-instruct-2507": {
                "details": {"family": "qwen2", "parameter_size": "3.1B", "quantization_level": "Q4_K_M"},
                "capabilities": ["completion"],
            }
        },
    )
    mgr = ModelManager(provider=OllamaProvider(transport=transport))
    rec = await mgr.verify_model_identity(
        role="intent_classifier",
        expectation=ModelIdentityExpectation(
            tag="qwen3:4b-instruct-2507",
            expected_family="qwen3",
            expected_parameter_billions=4.0,
            parameter_tolerance_billions=0.6,
        ),
    )
    assert rec.status == ModelVerificationStatus.IDENTITY_MISMATCH
    assert rec.available is False
    assert "Architecture mismatch" in (rec.mismatch_reason or "")


@pytest.mark.anyio
async def test_genuine_qwen3_embedding_acceptance():
    transport = _make_mock_ollama(
        tags_list=[{"name": "qwen3-embedding:0.6b", "digest": "ac6da0dfba84", "size": 639000000}],
        show_map={
            "qwen3-embedding:0.6b": {
                "details": {"family": "qwen3", "parameter_size": "595.78M", "quantization_level": "Q8_0"},
                "capabilities": ["embedding", "tools"],
            }
        },
    )
    mgr = ModelManager(provider=OllamaProvider(transport=transport))
    rec = await mgr.verify_model_identity(
        role="knowledge_retriever",
        expectation=ModelIdentityExpectation(
            tag="qwen3-embedding:0.6b",
            expected_family="qwen3",
            expected_parameter_billions=0.6,
            parameter_tolerance_billions=0.25,
            expected_capability="embedding",
        ),
    )
    assert rec.status == ModelVerificationStatus.VERIFIED
    assert rec.available is True


@pytest.mark.anyio
async def test_incorrectly_aliased_nomic_embedding_rejected():
    """A nomic-bert 137M model aliased as qwen3-embedding:0.6b must fail with IDENTITY_MISMATCH."""
    transport = _make_mock_ollama(
        tags_list=[{"name": "qwen3-embedding:0.6b", "digest": "0a109f422b47", "size": 274302450}],
        show_map={
            "qwen3-embedding:0.6b": {
                "details": {"family": "nomic-bert", "parameter_size": "137M", "quantization_level": "F16"},
                "capabilities": ["embedding"],
            }
        },
    )
    mgr = ModelManager(provider=OllamaProvider(transport=transport))
    rec = await mgr.verify_model_identity(
        role="knowledge_retriever",
        expectation=ModelIdentityExpectation(
            tag="qwen3-embedding:0.6b",
            expected_family="qwen3",
            expected_parameter_billions=0.6,
            expected_capability="embedding",
        ),
    )
    assert rec.status == ModelVerificationStatus.IDENTITY_MISMATCH
    assert rec.available is False


@pytest.mark.anyio
async def test_qwen25_coder_7b_verification():
    transport = _make_mock_ollama(
        tags_list=[{"name": "qwen2.5-coder:7b", "digest": "dae161e27b0e", "size": 4683087561}],
        show_map={
            "qwen2.5-coder:7b": {
                "details": {"family": "qwen2", "parameter_size": "7.6B", "quantization_level": "Q4_K_M"},
                "capabilities": ["completion", "tools"],
            }
        },
    )
    mgr = ModelManager(provider=OllamaProvider(transport=transport))
    rec = await mgr.verify_model_identity(
        role="sql_agent",
        expectation=ModelIdentityExpectation(
            tag="qwen2.5-coder:7b",
            expected_family="qwen2",
            expected_parameter_billions=7.6,
            expected_quantization="Q4_K_M",
            required=False,
        ),
    )
    assert rec.status == ModelVerificationStatus.VERIFIED
    assert rec.available is True


@pytest.mark.anyio
async def test_missing_model_handling():
    transport = _make_mock_ollama(tags_list=[], show_map={})
    mgr = ModelManager(provider=OllamaProvider(transport=transport))
    rec = await mgr.verify_model_identity(
        role="intent_classifier",
        expectation=ModelIdentityExpectation(tag="qwen3:4b-instruct-2507-q4_K_M", expected_family="qwen3"),
    )
    assert rec.status == ModelVerificationStatus.MODEL_NOT_FOUND
    assert rec.available is False


@pytest.mark.anyio
async def test_unsupported_capability_rejected():
    """An embedding-only model assigned to a completion role must fail with CAPABILITY_MISMATCH."""
    transport = _make_mock_ollama(
        tags_list=[{"name": "qwen3-embedding:0.6b", "digest": "ac6da0dfba84", "size": 639000000}],
        show_map={
            "qwen3-embedding:0.6b": {
                "details": {"family": "qwen3", "parameter_size": "595.78M", "quantization_level": "Q8_0"},
                "capabilities": ["embedding"],
            }
        },
    )
    mgr = ModelManager(provider=OllamaProvider(transport=transport))
    rec = await mgr.verify_model_identity(
        role="intent_classifier",
        expectation=ModelIdentityExpectation(
            tag="qwen3-embedding:0.6b",
            expected_family="qwen3",
            expected_capability="completion",
        ),
    )
    assert rec.status == ModelVerificationStatus.CAPABILITY_MISMATCH
    assert rec.available is False


@pytest.mark.anyio
async def test_ollama_unavailable_handling():
    def fail_handler(req):
        raise httpx.ConnectError("Connection refused")

    mgr = ModelManager(provider=OllamaProvider(transport=httpx.MockTransport(fail_handler)))
    rec = await mgr.verify_model_identity(
        role="intent_classifier",
        expectation=ModelIdentityExpectation(tag="qwen3:4b-instruct-2507-q4_K_M"),
    )
    assert rec.status == ModelVerificationStatus.VERIFICATION_UNAVAILABLE
    assert rec.available is False


@pytest.mark.anyio
async def test_model_digest_mismatch_detection():
    transport = _make_mock_ollama(
        tags_list=[{"name": "qwen3:4b-instruct-2507-q4_K_M", "digest": "wrongdigest999", "size": 2500000000}],
        show_map={
            "qwen3:4b-instruct-2507-q4_K_M": {
                "details": {"family": "qwen3", "parameter_size": "4.0B", "quantization_level": "Q4_K_M"},
                "capabilities": ["completion"],
            }
        },
    )
    mgr = ModelManager(provider=OllamaProvider(transport=transport))
    rec = await mgr.verify_model_identity(
        role="intent_classifier",
        expectation=ModelIdentityExpectation(
            tag="qwen3:4b-instruct-2507-q4_K_M",
            expected_family="qwen3",
            expected_digest="0edcdef34593",
        ),
    )
    assert rec.status == ModelVerificationStatus.IDENTITY_MISMATCH
    assert "Digest mismatch" in (rec.mismatch_reason or "")


def test_embedding_dimension_and_same_dimension_different_model_rejected():
    ev = EmbeddingValidator(expected_dimension=1024)
    with pytest.raises(IncompatibleEmbeddingDimensionError):
        ev.validate_vector([0.1] * 768)

    # Same dimension (768 vs 768) but different model/digest must be rejected
    with pytest.raises(IncompatibleEmbeddingDimensionError, match="Index model mismatch"):
        ev.check_index_compatibility(
            index_dimension=768,
            new_model_dimension=768,
            index_model_tag="nomic-embed-text:latest",
            new_model_tag="qwen3-embedding:0.6b",
        )


@pytest.mark.anyio
async def test_inference_rejected_when_role_failed_verification():
    transport = _make_mock_ollama(
        tags_list=[{"name": "qwen3:4b-instruct-2507-q4_K_M", "digest": "bad", "size": 100}],
        show_map={
            "qwen3:4b-instruct-2507-q4_K_M": {
                "details": {"family": "qwen2", "parameter_size": "3.1B", "quantization_level": "Q4_K_M"},
            }
        },
    )
    provider = OllamaProvider(transport=transport)
    mgr = ModelManager(provider=provider)
    await mgr.verify_model_identity(
        role="intent_classifier",
        expectation=ModelIdentityExpectation(tag="qwen3:4b-instruct-2507-q4_K_M", expected_family="qwen3"),
    )
    client = LLMClient(provider=provider, manager=mgr)
    with pytest.raises(ModelVerificationError, match="Inference blocked"):
        await client.generate_completion(prompt="Hello", role="intent_classifier")


def test_configuration_driven_model_selection():
    mgr = ModelManager()
    assert mgr.get_configured_model("intent_classifier") == "qwen3:4b-instruct-2507-q4_K_M"
    assert mgr.get_configured_model("knowledge_retriever") == "qwen3-embedding:0.6b"
    assert mgr.get_configured_model("sql_agent") == "qwen2.5-coder:7b"


def test_metadata_models_api_validation_and_auth():
    app = create_app()
    client = TestClient(app)

    # Non-admin rejected
    r_denied = client.get("/v1/metadata/models")
    assert r_denied.status_code == 403

    # Admin allowed
    r_ok = client.get("/v1/metadata/models", headers={"Authorization": "Bearer netiq-admin-dev-token"})
    assert r_ok.status_code == 200
    body = r_ok.json()
    assert "models" in body
    assert body["count"] >= 1
    first = body["models"][0]
    for key in ("role", "configured_model_tag", "status", "available", "last_verified_at"):
        assert key in first
