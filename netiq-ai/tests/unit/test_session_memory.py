"""Session management (task 1.6): chat store, circle rule and history policy."""

import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.adapters.llm.provider import LLMProviderError
from src.session import chat_store, chat_summary
from src.session.history_policy import NO_HISTORY, history_for_question, looks_like_followup
from src.session.identity import ALL_CIRCLES, allowed_circles, circles_in_text, normalize_circle


@pytest.fixture(autouse=True)
def chat_db(tmp_path, monkeypatch):
    path = tmp_path / "chat.db"
    monkeypatch.setenv("CHAT_DB_PATH", str(path))
    return path


def test_chats_are_private_to_their_user():
    chat = chat_store.create_conversation("alice")
    chat_store.add_message("alice", chat, "user", "how many 4G cells in MH?")
    assert [c["conversation_id"] for c in chat_store.list_conversations("alice")] == [chat]
    assert chat_store.list_conversations("bob") == []
    with pytest.raises(chat_store.ConversationNotFound):
        chat_store.get_messages("bob", chat)
    with pytest.raises(chat_store.ConversationNotFound):
        chat_store.add_message("bob", chat, "user", "let me in")


def test_short_term_window_keeps_the_newest_turns_in_order(monkeypatch):
    monkeypatch.setenv("HISTORY_WINDOW_MESSAGES", "3")
    chat = chat_store.create_conversation("alice")
    for i in range(5):
        chat_store.add_message("alice", chat, "user", f"q{i}")
    assert [m.content for m in chat_store.recent_messages("alice", chat)] == ["q2", "q3", "q4"]
    assert chat_store.list_conversations("alice")[0]["title"] == "q0"  # first question = one-line title


def test_state_merges_and_none_removes():
    chat = chat_store.create_conversation("alice")
    chat_store.update_state("alice", chat, last_report="ran_cell_4g", filters={"circle": "MH"})
    assert chat_store.update_state("alice", chat, filters=None) == {"last_report": "ran_cell_4g"}
    assert chat_store.get_state("alice", chat) == {"last_report": "ran_cell_4g"}


def test_keywords_count_up_per_user():
    chat_store.record_keywords("alice", {"circle": ["mh", "GJ"]})
    chat_store.record_keywords("alice", {"circle": ["MH"], "report": [""]})
    assert chat_store.top_keywords("alice")[0] == {"kind": "circle", "keyword": "MH", "hits": 2}
    assert chat_store.top_keywords("bob") == []


def test_old_chats_and_keywords_are_purged(chat_db):
    old = chat_store.create_conversation("alice")
    chat_store.add_message("alice", old, "user", "old question")
    chat_store.record_keywords("alice", {"circle": ["KK"]})
    with sqlite3.connect(chat_db) as conn:
        conn.execute("UPDATE conversations SET updated_at = '2000-01-01T00:00:00+00:00'")
        conn.execute("UPDATE user_keywords SET last_used = '2000-01-01T00:00:00+00:00'")
    fresh = chat_store.create_conversation("alice")  # starting a chat runs the purge
    assert [c["conversation_id"] for c in chat_store.list_conversations("alice")] == [fresh]
    assert chat_store.top_keywords("alice") == []
    with sqlite3.connect(chat_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0


def _fake_llm(prompts, reply='"Asked about 4G cells in MU."\nextra line'):
    class FakeLLM:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *exc): pass
        async def generate(self, prompt, **kwargs):
            prompts.append(prompt)
            if reply is None:
                raise LLMProviderError("Ollama is down")
            return SimpleNamespace(response_text=reply)
    return FakeLLM


def test_left_chats_get_one_summary_that_outlives_the_chat(chat_db, monkeypatch):
    prompts = []
    monkeypatch.setattr(chat_summary, "OllamaProvider", _fake_llm(prompts))
    chat = chat_store.create_conversation("alice")
    chat_store.add_message("alice", chat, "user", "how many 4G cells in MU?")
    chat_store.add_message("alice", chat, "assistant", "Chat is not connected to the orchestrator yet.")

    asyncio.run(chat_summary.summarise_left_chats("alice", skip=chat))  # still in use: no LLM call
    assert prompts == []
    asyncio.run(chat_summary.summarise_left_chats("alice"))
    assert chat_store.list_conversations("alice")[0]["summary"] == "Asked about 4G cells in MU."
    assert "4G cells in MU" in prompts[0] and "orchestrator" not in prompts[0]  # questions only
    asyncio.run(chat_summary.summarise_left_chats("alice"))  # no new questions: not written again
    assert len(prompts) == 1

    old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    with sqlite3.connect(chat_db) as conn:
        conn.execute("UPDATE conversations SET updated_at = ?", (old,))
    chat_store.create_conversation("alice")  # purge: the 40-day-old chat goes, its summary stays (90 days)
    with sqlite3.connect(chat_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
        assert conn.execute("SELECT summary FROM chat_summaries").fetchone()[0] == "Asked about 4G cells in MU."
        conn.execute("UPDATE chat_summaries SET updated_at = '2000-01-01T00:00:00+00:00'")
    chat_store.create_conversation("alice")
    with sqlite3.connect(chat_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM chat_summaries").fetchone()[0] == 0


def test_llm_failure_only_means_no_summary_yet(monkeypatch):
    monkeypatch.setattr(chat_summary, "OllamaProvider", _fake_llm([], reply=None))
    chat = chat_store.create_conversation("alice")
    chat_store.add_message("alice", chat, "user", "how many sites in BR?")
    asyncio.run(chat_summary.summarise_left_chats("alice"))
    assert chat_store.list_conversations("alice")[0]["summary"] is None
    assert chat_store.chats_needing_summary("alice")[0]["conversation_id"] == chat  # tried again later


def test_circle_rule_matches_netiq():
    assert allowed_circles([]) == (ALL_CIRCLES,)               # empty list = all circles (team rule)
    assert allowed_circles(None) == (ALL_CIRCLES,)
    assert allowed_circles(["mh", "PAN INDIA"]) == (ALL_CIRCLES,)
    assert allowed_circles(["UPE", "mh", "MH, Karnataka"]) == ("UE", "MH", "KK")
    assert normalize_circle("MH - Maharashtra") == "MH"


def test_circles_named_in_the_question():
    assert circles_in_text("how many sites in Gujarat ?") == ["GJ"]
    assert circles_in_text("compare Mumbai and New Delhi 4G cells") == ["MU", "DL"]
    assert circles_in_text("show the same for GJ circle") == ["GJ"]
    assert circles_in_text("Uttar Pradesh East vs tamil  nadu") == ["UE", "TN"]  # longest name wins
    assert circles_in_text("har circle ka count, in which OR is it, Punjabi users") == []  # everyday words
    assert circles_in_text("how many 4G cells?") == []


def _turns(*pairs):
    return [chat_store.Message(role, text, "t") for role, text in pairs]


def test_standalone_questions_get_no_history():
    before = _turns(("user", "how many 4G cells in MH?"), ("assistant", "There are 1,234 4G cells in MH."))
    assert history_for_question("how many sites are in BR circle?", before) == NO_HISTORY
    assert history_for_question("what is the node count for GJ?", before) == NO_HISTORY
    assert history_for_question("anything", []) == NO_HISTORY


def test_followups_get_a_short_window_without_failed_answers():
    before = _turns(("user", "how many 4G cells in MH?"), ("assistant", "Chat is not connected to the orchestrator yet."))
    for q in ("and 5G?", "aur 5G cells kitne hain", "show the same for GJ circle", "iska vendor kya hai"):
        assert looks_like_followup(q, before), q
    text = history_for_question("and 5G?", before)
    assert "User: how many 4G cells in MH?" in text and "orchestrator" not in text
