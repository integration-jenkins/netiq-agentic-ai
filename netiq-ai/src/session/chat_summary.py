"""One-line chat summaries for long-term memory, written by the local LLM in the background.

A chat is summarised once the user has left it: they asked in another chat, started a new
chat, or came back after the chat was quiet longer than the login idle timeout. The chat in
use is never summarised, so the LLM does not run on every message. A summary is written
again only when the chat has new questions.

The model is the `chat_summarizer` role in configs/models.yaml; CHAT_SUMMARY_MODEL (env)
overrides it, e.g. when that model is not installed on a machine. If Ollama fails, the chat
simply has no summary yet; chatting is never affected.
"""

from __future__ import annotations

import logging
import os
import threading

from src.adapters.llm.provider import LLMProviderError, OllamaProvider
from src.session import chat_store

log = logging.getLogger(__name__)

# ponytail: one summary run at a time for all users; a queue per user if many users chat at once.
_busy = threading.Lock()

_PROMPT = """These are the questions a user asked in one chat with NETIQ, a telecom network tool.
Write ONE line of at most 20 words saying what they asked about. Keep the exact names they
used for circles, cities, sites, technologies (2G/3G/4G/5G), reports and vendors.
Reply with the line only.

Questions:
{questions}"""


def _questions(messages: list[chat_store.Message]) -> str:
    # Only the questions: they carry the topic, and no answers means no numbers to repeat.
    lines = [f"- {' '.join(m.content.split())[:300]}" for m in messages if m.role == "user"]
    return "\n".join(lines)[-3000:]


def _one_line(text: str) -> str:
    lines = [ln.strip().strip('"').strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[0][:200] if lines else ""


async def summarise_left_chats(user_id: str, skip: str | None = None, quiet_since: str | None = None) -> None:
    """Background task: summarise the user's chats that have new questions (see module docstring)."""
    if not _busy.acquire(blocking=False):
        return  # a run is already going; the next request picks up whatever is left
    try:
        chats = chat_store.chats_needing_summary(user_id, skip=skip, quiet_since=quiet_since)
        if not chats:
            return
        # Runs after the reply is sent, so it can wait for a cold model load (~25 s+ on this kind of machine).
        async with OllamaProvider(timeout_seconds=120) as llm:
            for chat in chats:
                try:
                    messages = chat_store.get_messages(user_id, chat["conversation_id"])
                    result = await llm.generate(_PROMPT.format(questions=_questions(messages)),
                                                model=os.getenv("CHAT_SUMMARY_MODEL") or None,
                                                role="chat_summarizer")
                except chat_store.ConversationNotFound:
                    continue  # deleted meanwhile
                except LLMProviderError as exc:
                    log.warning("Chat summary skipped: %s", exc)
                    return
                line = _one_line(result.response_text)
                if line:
                    chat_store.save_summary(user_id, chat["conversation_id"], chat["title"], line, chat["questions"])
    finally:
        _busy.release()
