"""Chat memory for NETIQ AI, kept in one SQLite file.

What is stored
--------------
conversations  one row per chat: owner, one-line title (the first question) and the chat
               state (last report, filters, a question waiting for the user's answer).
messages       every user question and assistant answer of a chat. Only text plus a small
               `meta` dict (report id, filters, row count). Never the data rows themselves.
user_keywords  long-term memory: the circles, reports, vendors... a user asks about, with a
               hit count. A hint for understanding vague questions, never an access filter.
chat_summaries long-term memory: one line per chat written by the local LLM
               (src/session/chat_summary.py). It outlives the chat's messages.

Rules
-----
* Every read and write is scoped by user_id (the NETIQ username). A chat that belongs to
  someone else behaves exactly like a chat that does not exist (ConversationNotFound).
* Chats not touched for CHAT_RETENTION_DAYS, and keywords and summaries not used for
  KEYWORD_RETENTION_DAYS, are deleted when a new chat is started.

Who is logged in is NOT decided here: src/security/netiq_login.py owns the login session
and its 30-minute idle timeout. This module only keeps the chats of a known user.

Settings (environment): CHAT_DB_PATH, HISTORY_WINDOW_MESSAGES (10), CHAT_RETENTION_DAYS (30),
KEYWORD_RETENTION_DAYS (90).
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "session" / "chat_history.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    title           TEXT,
    state           TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    message_id      TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id         TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    meta            TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_keywords (
    user_id   TEXT NOT NULL,
    kind      TEXT NOT NULL,
    keyword   TEXT NOT NULL,
    hits      INTEGER NOT NULL DEFAULT 0,
    last_used TEXT NOT NULL,
    PRIMARY KEY (user_id, kind, keyword)
);
CREATE TABLE IF NOT EXISTS chat_summaries (
    conversation_id TEXT PRIMARY KEY,  -- no foreign key: the summary stays after the chat is deleted
    user_id         TEXT NOT NULL,
    title           TEXT,
    summary         TEXT NOT NULL,
    questions       INTEGER NOT NULL,  -- user questions the summary covers; more means it is out of date
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_summaries_user ON chat_summaries(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
"""


class ConversationNotFound(KeyError):
    """The chat does not exist, or it belongs to another user."""


@dataclass(frozen=True)
class Message:
    role: str
    content: str
    created_at: str
    meta: dict[str, Any] = field(default_factory=dict)


def _now() -> str:
    # Microseconds keep messages written in the same second in the right order.
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _int_setting(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _connect() -> sqlite3.Connection:
    path = Path(os.getenv("CHAT_DB_PATH") or _DEFAULT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(_SCHEMA)  # cheap no-op once the tables exist
    return conn


def _owned(conn: sqlite3.Connection, user_id: str, conversation_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM conversations WHERE conversation_id = ? AND user_id = ?",
        (conversation_id, user_id),
    ).fetchone()
    if row is None:
        raise ConversationNotFound(conversation_id)
    return row


# ----------------------------------------------------------------- conversations

def create_conversation(user_id: str) -> str:
    """Start a new chat for this user and return its id. Also clears expired chats."""
    purge_expired()
    conversation_id = uuid.uuid4().hex
    now = _now()
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO conversations (conversation_id, user_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conversation_id, user_id, now, now),
        )
    return conversation_id


def list_conversations(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """The user's own chats, most recently used first, with their one-line summary (None until written)."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            """SELECT c.conversation_id, c.title, s.summary, c.created_at, c.updated_at FROM conversations c
               LEFT JOIN chat_summaries s ON s.conversation_id = c.conversation_id
               WHERE c.user_id = ? ORDER BY c.updated_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- messages

def add_message(user_id: str, conversation_id: str, role: str, content: str,
                meta: dict[str, Any] | None = None) -> None:
    """Store one turn. The first user question becomes the chat's one-line title."""
    now = _now()
    with closing(_connect()) as conn, conn:
        chat = _owned(conn, user_id, conversation_id)
        conn.execute(
            """INSERT INTO messages (message_id, conversation_id, user_id, role, content, meta, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (uuid.uuid4().hex, conversation_id, user_id, role, content, json.dumps(meta or {}), now),
        )
        title = chat["title"] or (" ".join(content.split())[:120] if role == "user" else None)
        conn.execute(
            "UPDATE conversations SET updated_at = ?, title = ? WHERE conversation_id = ?",
            (now, title, conversation_id),
        )


def get_messages(user_id: str, conversation_id: str, limit: int | None = None) -> list[Message]:
    """The newest `limit` turns of the user's own chat (all when None), oldest first."""
    with closing(_connect()) as conn:
        _owned(conn, user_id, conversation_id)
        rows = conn.execute(
            """SELECT role, content, meta, created_at FROM messages
               WHERE conversation_id = ? AND user_id = ?
               ORDER BY created_at DESC, rowid DESC LIMIT ?""",
            (conversation_id, user_id, -1 if limit is None else limit),
        ).fetchall()
    return [Message(r["role"], r["content"], r["created_at"], json.loads(r["meta"])) for r in reversed(rows)]


def recent_messages(user_id: str, conversation_id: str) -> list[Message]:
    """Short-term memory: the last HISTORY_WINDOW_MESSAGES turns of this chat."""
    return get_messages(user_id, conversation_id, _int_setting("HISTORY_WINDOW_MESSAGES", 10))


# ----------------------------------------------------------------- chat state

def get_state(user_id: str, conversation_id: str) -> dict[str, Any]:
    """Last report, filters and pending question of the chat (empty dict at the start)."""
    with closing(_connect()) as conn:
        return json.loads(_owned(conn, user_id, conversation_id)["state"])


def update_state(user_id: str, conversation_id: str, **changes: Any) -> dict[str, Any]:
    """Merge `changes` into the chat state; a value of None removes that key."""
    with closing(_connect()) as conn, conn:
        state = json.loads(_owned(conn, user_id, conversation_id)["state"])
        state.update(changes)
        state = {k: v for k, v in state.items() if v is not None}
        conn.execute(
            "UPDATE conversations SET state = ? WHERE conversation_id = ?",
            (json.dumps(state), conversation_id),
        )
    return state


# ----------------------------------------------------------------- long-term keywords

def record_keywords(user_id: str, keywords: dict[str, Iterable[str]]) -> None:
    """Count what the user asked about, e.g. {"circle": ["MH"], "report": ["ran_cell_4g"]}."""
    now = _now()
    rows = [(user_id, kind, str(word).strip().upper(), now)
            for kind, words in keywords.items() for word in words if str(word).strip()]
    if not rows:
        return
    with closing(_connect()) as conn, conn:
        conn.executemany(
            """INSERT INTO user_keywords (user_id, kind, keyword, hits, last_used) VALUES (?, ?, ?, 1, ?)
               ON CONFLICT (user_id, kind, keyword) DO UPDATE SET hits = hits + 1, last_used = excluded.last_used""",
            rows,
        )


def top_keywords(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """The user's most frequent keywords, as a hint for vague questions."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            """SELECT kind, keyword, hits FROM user_keywords WHERE user_id = ?
               ORDER BY hits DESC, last_used DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- long-term chat summaries

def chats_needing_summary(user_id: str, skip: str | None = None, quiet_since: str | None = None,
                          limit: int = 3) -> list[dict[str, Any]]:
    """The user's chats with questions their summary does not cover yet, newest first.

    skip: the chat in use right now. quiet_since: only chats not touched after this time.
    """
    with closing(_connect()) as conn:
        rows = conn.execute(
            """SELECT c.conversation_id, c.title, COUNT(m.message_id) AS questions FROM conversations c
               JOIN messages m ON m.conversation_id = c.conversation_id AND m.role = 'user'
               LEFT JOIN chat_summaries s ON s.conversation_id = c.conversation_id
               WHERE c.user_id = ? AND c.conversation_id IS NOT ? AND (? IS NULL OR c.updated_at < ?)
               GROUP BY c.conversation_id HAVING COUNT(m.message_id) > COALESCE(MAX(s.questions), 0)
               ORDER BY c.updated_at DESC LIMIT ?""",
            (user_id, skip, quiet_since, quiet_since, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def save_summary(user_id: str, conversation_id: str, title: str | None, summary: str, questions: int) -> None:
    """Store (or replace) the one-line summary of a chat."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            """INSERT INTO chat_summaries (conversation_id, user_id, title, summary, questions, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (conversation_id) DO UPDATE SET title = excluded.title, summary = excluded.summary,
                   questions = excluded.questions, updated_at = excluded.updated_at
               WHERE chat_summaries.user_id = excluded.user_id""",
            (conversation_id, user_id, title, summary, questions, _now()),
        )


# ----------------------------------------------------------------- retention

def purge_expired() -> None:
    """Delete chats, keywords and summaries that have not been used within their retention period."""
    now = datetime.now(timezone.utc)
    chat_cutoff = (now - timedelta(days=_int_setting("CHAT_RETENTION_DAYS", 30))).isoformat(timespec="microseconds")
    word_cutoff = (now - timedelta(days=_int_setting("KEYWORD_RETENTION_DAYS", 90))).isoformat(timespec="microseconds")
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM conversations WHERE updated_at < ?", (chat_cutoff,))  # messages go too (cascade)
        conn.execute("DELETE FROM user_keywords WHERE last_used < ?", (word_cutoff,))
        conn.execute("DELETE FROM chat_summaries WHERE updated_at < ?", (word_cutoff,))
