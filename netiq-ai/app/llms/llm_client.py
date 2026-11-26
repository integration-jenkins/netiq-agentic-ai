"""Application-facing LLM client for NETIQ agents and workflows."""

from typing import Any
from app.llms.model_manager import ModelManager, default_model_manager
from app.llms.model_registry import ModelVerificationError, ModelVerificationStatus
from app.llms.prompts import (
    INTENT_CLASSIFICATION_SYSTEM_PROMPT,
    REPORT_SELECTION_SYSTEM_PROMPT,
    SQL_AGENT_SYSTEM_PROMPT,
)
from src.adapters.llm.provider import LLMResult, OllamaProvider, default_llm_provider


class LLMClient:
    """High-level client providing specialized agent completion methods."""

    def __init__(self, provider: OllamaProvider | None = None, manager: ModelManager | None = None) -> None:
        self.provider = provider or default_llm_provider
        self.manager = manager or default_model_manager

    async def generate_completion(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        role: str | None = None,
    ) -> LLMResult:
        """Generic completion with speed, quality metrics, and identity verification guard."""
        if role and not self.manager.is_role_available(role):
            rec = self.manager.get_identity_records().get(role)
            reason = rec.mismatch_reason if rec else f"Role '{role}' failed model identity verification."
            status = rec.status if rec else ModelVerificationStatus.IDENTITY_MISMATCH
            raise ModelVerificationError(
                f"Inference blocked for role '{role}': {reason}",
                status=status,
            )

        return await self.provider.generate(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            role=role,
        )

    async def classify_intent(self, query: str, model: str | None = None) -> LLMResult:
        """Classify user query into REPORT, SQL, KNOWLEDGE, or COMPARISON."""
        return await self.provider.generate(
            prompt=f'Query: "{query}"\nClassification:',
            model=model,
            system_prompt=INTENT_CLASSIFICATION_SYSTEM_PROMPT,
            role="intent_classifier",
        )

    async def select_report(self, query: str, candidate_reports: list[str], model: str | None = None) -> LLMResult:
        """Select matching report from candidate report IDs."""
        candidates_str = ", ".join(candidate_reports)
        prompt = f"Query: \"{query}\"\nCandidate Reports: [{candidates_str}]\nSelected Report ID:"
        return await self.provider.generate(
            prompt=prompt,
            model=model,
            system_prompt=REPORT_SELECTION_SYSTEM_PROMPT,
            role="report_selector",
        )

    async def generate_sql(self, requirement: str, schema_info: str | None = None, model: str | None = None) -> LLMResult:
        """Generate read-only Oracle SQL for telecom queries."""
        schema_ctx = f"\nDatabase Schema Context:\n{schema_info}" if schema_info else ""
        prompt = f"Requirement: {requirement}{schema_ctx}\nSQL Query:"
        return await self.provider.generate(
            prompt=prompt,
            model=model,
            system_prompt=SQL_AGENT_SYSTEM_PROMPT,
            role="sql_agent",
        )


default_llm_client = LLMClient()
