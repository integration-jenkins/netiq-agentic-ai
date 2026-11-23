"""Unit tests for Knowledge Agent grounding, threshold evaluation, and anti-hallucination."""

import httpx
import pytest
from app.llms.knowledge_agent import (
    KnowledgeAgent,
    KnowledgeDocument,
    default_knowledge_agent,
)
from app.llms.llm_client import default_llm_client
from src.adapters.llm.provider import OllamaProvider


def mock_sop_ollama_with_hallucination(request: httpx.Request) -> httpx.Response:
    """Simulates an LLM trying to hallucinate Severity-1 from SOP-RAN-402."""
    return httpx.Response(200, json={
        "model": "qwen3:4b-instruct-2507",
        "response": (
            "Based on the provided context, an availability drop below 98.5% triggers Severity-2. "
            "However, when cell availability falls to 97%, it might trigger Severity-1."
        ),
        "eval_count": 25,
        "eval_duration": 100000000,
        "prompt_eval_count": 50,
        "prompt_eval_duration": 50000000,
        "done": True,
    })


def mock_sop_ollama_compliant(request: httpx.Request) -> httpx.Response:
    """Simulates compliant LLM answering Severity-2 without hallucinating Severity-1."""
    return httpx.Response(200, json={
        "model": "qwen3:4b-instruct-2507",
        "response": (
            "According to [SOP-RAN-402], an eNodeB cell availability drop below 98.5% triggers Severity-2 "
            "and notification to the NOC RAN team. Therefore, when cell availability falls to 97% (below 98.5%), "
            "Severity-2 is triggered and the NOC RAN team must be notified."
        ),
        "eval_count": 35,
        "eval_duration": 150000000,
        "prompt_eval_count": 50,
        "prompt_eval_duration": 50000000,
        "done": True,
    })


@pytest.mark.anyio
async def test_mandatory_sop_ran_402_deterministic_threshold_evaluation():
    """Mandatory Test:
    Source: SOP-RAN-402: eNodeB cell availability below 98.5% triggers Severity-2 and notification to the NOC RAN team.
    Question: What happens when eNodeB cell availability falls to 97%?
    Expected: Severity-2 is triggered and notification to the NOC RAN team. Must NOT invent Severity-1.
    """
    doc = KnowledgeDocument(
        doc_id="SOP-RAN-402",
        title="RAN Cell Availability and Incident Escalation",
        domain="RAN",
        content="SOP-RAN-402: eNodeB cell availability below 98.5% triggers Severity-2 and notification to the NOC RAN team.",
    )

    # Test deterministic rule engine
    agent = KnowledgeAgent()
    sev, rule = agent.evaluate_threshold_rule(
        query="What happens when eNodeB cell availability falls to 97%?",
        document_text=doc.content,
    )
    assert sev == "Severity-2"
    assert "97.0% falls below the 98.5% threshold" in rule


@pytest.mark.anyio
async def test_mandatory_sop_anti_hallucination_catches_fabricated_severity_1():
    """If the LLM generates an unmentioned severity level (Severity-1), anti-hallucination guard catches it."""
    doc = KnowledgeDocument(
        doc_id="SOP-RAN-402",
        title="RAN Cell Availability and Incident Escalation",
        domain="RAN",
        content="SOP-RAN-402: eNodeB cell availability below 98.5% triggers Severity-2 and notification to the NOC RAN team.",
    )

    # Inject hallucinating mock provider
    default_llm_client.provider = OllamaProvider(transport=httpx.MockTransport(mock_sop_ollama_with_hallucination))

    agent = KnowledgeAgent()
    ans = await agent.answer_question(
        query="What happens when eNodeB cell availability falls to 97%?",
        documents=[doc],
    )

    # Verify that the response does NOT contain Severity-1 and correctly identifies Severity-2
    assert "Severity-1" not in ans.answer
    assert "Severity-2" in ans.answer
    assert ans.status == "GROUNDED"
    assert "SOP-RAN-402" in ans.cited_sources


@pytest.mark.anyio
async def test_knowledge_agent_insufficient_evidence():
    """When no documents or irrelevant documents are provided, returns INSUFFICIENT_EVIDENCE."""
    agent = KnowledgeAgent()

    # Empty docs
    ans = await agent.answer_question(query="What is the microwave frequency in Kolkata?", documents=[])
    assert ans.status == "INSUFFICIENT_EVIDENCE"
    assert "INSUFFICIENT_EVIDENCE" in ans.answer


@pytest.mark.anyio
async def test_knowledge_agent_grounded_answer():
    """Compliant answer with proper source attribution."""
    doc = KnowledgeDocument(
        doc_id="SOP-RAN-402",
        title="RAN Cell Availability",
        domain="RAN",
        content="SOP-RAN-402: eNodeB cell availability below 98.5% triggers Severity-2 and notification to the NOC RAN team.",
    )
    default_llm_client.provider = OllamaProvider(transport=httpx.MockTransport(mock_sop_ollama_compliant))

    agent = KnowledgeAgent()
    ans = await agent.answer_question(
        query="What happens when eNodeB cell availability falls to 97%?",
        documents=[doc],
    )
    assert ans.status == "GROUNDED"
    assert "Severity-2" in ans.answer
    assert "Severity-1" not in ans.answer
    assert "SOP-RAN-402" in ans.cited_sources
