"""Unit tests for local Ollama LLM provider, model manager, and inference endpoint."""

import httpx
import pytest
from app.llms.llm_client import LLMClient
from app.llms.model_manager import ModelManager
from src.adapters.llm.provider import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaProvider,
)
from src.api.app import create_app
from src.api.routes.inference import InferenceRequest


def mock_ollama_generate_handler(request: httpx.Request) -> httpx.Response:
    """Mock transport simulating local Ollama /api/generate endpoint."""
    if request.url.path == "/api/generate":
        import json
        body = json.loads(request.content.decode("utf-8"))
        model = body.get("model", "qwen2.5:3b")

        if model == "non_existent_model":
            return httpx.Response(404, json={"error": "model 'non_existent_model' not found"})

        resp_payload = {
            "model": model,
            "created_at": "2026-11-23T10:00:00.000000Z",
            "response": "REPORT",
            "done": True,
            "total_duration": 450000000,       # 0.45s
            "load_duration": 50000000,         # 0.05s
            "prompt_eval_count": 25,
            "prompt_eval_duration": 100000000, # 0.1s
            "eval_count": 2,                   # 2 tokens
            "eval_duration": 66000000,         # 0.066s (approx 30.3 tok/s)
        }
        return httpx.Response(200, json=resp_payload)

    elif request.url.path == "/api/tags":
        return httpx.Response(200, json={
            "models": [
                {"name": "qwen2.5:3b"},
                {"name": "qwen2.5-coder:7b"},
            ]
        })

    return httpx.Response(404)


@pytest.mark.anyio
async def test_ollama_provider_metrics_calculation():
    transport = httpx.MockTransport(mock_ollama_generate_handler)
    provider = OllamaProvider(transport=transport)

    result = await provider.generate(prompt="Classify query", model="qwen2.5:3b")

    assert result.model == "qwen2.5:3b"
    assert result.response_text == "REPORT"
    assert result.metrics.eval_count_tokens == 2
    assert result.metrics.prompt_eval_count_tokens == 25
    assert result.metrics.eval_tokens_per_second > 25.0
    assert result.metrics.total_duration_seconds > 0.0

    await provider.close()


@pytest.mark.anyio
async def test_ollama_provider_model_not_found():
    transport = httpx.MockTransport(mock_ollama_generate_handler)
    provider = OllamaProvider(transport=transport)

    with pytest.raises(OllamaModelNotFoundError, match="not found on Ollama"):
        await provider.generate(prompt="Test", model="non_existent_model")

    await provider.close()


@pytest.mark.anyio
async def test_ollama_provider_connection_failure():
    def fail_handler(req):
        raise httpx.ConnectError("Connection refused on 11434")

    transport = httpx.MockTransport(fail_handler)
    provider = OllamaProvider(transport=transport)

    with pytest.raises(OllamaConnectionError, match="Cannot connect to local Ollama"):
        await provider.generate(prompt="Test")

    await provider.close()


def test_model_manager_resolves_configured_roles():
    manager = ModelManager()

    # Default configured model
    default_model = manager.get_configured_model()
    assert "qwen" in default_model.lower()

    # SQL Agent specific role model
    sql_model = manager.get_configured_model(role="sql_agent")
    assert "coder" in sql_model.lower() or "7b" in sql_model.lower()

    # Intent classifier role model
    intent_model = manager.get_configured_model(role="intent_classifier")
    assert "qwen" in intent_model.lower()


@pytest.mark.anyio
async def test_inference_endpoint_via_asgi(monkeypatch):
    """Test POST /v1/inference route registered in FastAPI."""
    app = create_app()

    # Inject mock provider into LLM client for deterministic testing
    from app.llms.llm_client import default_llm_client
    mock_provider = OllamaProvider(transport=httpx.MockTransport(mock_ollama_generate_handler))
    monkeypatch.setattr(default_llm_client, "provider", mock_provider)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/v1/inference",
            json={
                "prompt": "Show 4G cell availability for Delhi",
                "role": "intent_classifier",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["response"] == "REPORT"
        assert data["model"] == "qwen3:4b-instruct-2507"
        assert "metrics" in data
        assert data["metrics"]["eval_count_tokens"] == 2
        assert data["metrics"]["eval_tokens_per_second"] > 0

    # Also test explicit display name override
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/v1/inference",
            json={
                "prompt": "Show 4G cell availability for Delhi",
                "model": "Qwen3 4B Instruct 2507",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["model"] == "qwen3:4b-instruct-2507"
