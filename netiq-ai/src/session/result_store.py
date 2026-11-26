"""Verified result store and session conversation context for pagination and Excel export.

Architecture Role:
------------------
Stores verified backend query results keyed by `result_id` so that:
1. Pagination (`GET /v1/results/{result_id}`) serves slices of the exact verified result
   without re-running expensive queries or drifting data versions.
2. Excel Export (`POST /v1/export`) exports the complete verified result (not only page 0)
   with original filters, data version, and data date preserved.
3. Ownership & Authorization: Every result records its `owner_username` and `circle`,
   enforcing access checks before serving pages or exports.
4. Session Context: Maintains per-session follow-up state (last report, filters, result_id).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.schemas.chat import ColumnMeta, SourceReference


@dataclass
class VerifiedResult:
    """Immutable snapshot of a verified report or comparison query result."""
    result_id: str
    owner_username: str
    report_id: str | None
    report_name: str | None
    circle: str | None
    domain: str | None
    columns: list[ColumnMeta]
    rows: list[dict[str, Any]]
    sources: list[SourceReference]
    applied_filters: dict[str, Any]
    data_version: str | None
    data_as_of: str | None
    mode: str
    created_at: float = field(default_factory=time.time)


@dataclass
class SessionConversationState:
    """Authoritative backend session state for follow-up questions."""
    session_id: str
    owner_username: str
    last_report_id: str | None = None
    last_report_name: str | None = None
    last_circle: str | None = None
    last_domain: str | None = None
    last_result_id: str | None = None
    last_filters: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, str]] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


class ResultNotFoundError(Exception):
    """Raised when a result_id does not exist or has expired."""


class ResultAccessDeniedError(Exception):
    """Raised when a user requests a result they do not own or lack circle access to."""


class ResultStore:
    """Thread-safe in-memory store for verified results and session context."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._lock = threading.Lock()
        self._results: dict[str, VerifiedResult] = {}
        self._sessions: dict[str, SessionConversationState] = {}
        self._ttl = ttl_seconds

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [rid for rid, r in self._results.items() if now - r.created_at > self._ttl]
        for rid in expired:
            del self._results[rid]

    def save_result(
        self,
        owner_username: str,
        report_id: str | None,
        report_name: str | None,
        circle: str | None,
        domain: str | None,
        columns: list[ColumnMeta],
        rows: list[dict[str, Any]],
        sources: list[SourceReference],
        applied_filters: dict[str, Any],
        data_version: str | None,
        data_as_of: str | None,
        mode: str,
        result_id: str | None = None,
    ) -> VerifiedResult:
        rid = result_id or f"res-{uuid.uuid4().hex[:12]}"
        record = VerifiedResult(
            result_id=rid,
            owner_username=owner_username,
            report_id=report_id,
            report_name=report_name,
            circle=circle,
            domain=domain,
            columns=columns,
            rows=rows,
            sources=sources,
            applied_filters=applied_filters,
            data_version=data_version,
            data_as_of=data_as_of,
            mode=mode,
        )
        with self._lock:
            self._purge_expired()
            self._results[rid] = record
        return record

    def get_result(
        self,
        result_id: str,
        username: str,
        is_admin: bool = False,
        permitted_circles: list[str] | None = None,
    ) -> VerifiedResult:
        with self._lock:
            self._purge_expired()
            record = self._results.get(result_id)
        if not record:
            raise ResultNotFoundError(f"Result '{result_id}' was not found or has expired.")
        if not is_admin and record.owner_username != username:
            raise ResultAccessDeniedError(f"User '{username}' is not authorized to access result '{result_id}'.")
        if not is_admin and record.circle and permitted_circles is not None and "*" not in permitted_circles:
            allowed = {c.strip().upper() for c in permitted_circles}
            if record.circle.strip().upper() not in allowed:
                raise ResultAccessDeniedError(
                    f"User '{username}' is not authorized for circle '{record.circle}'."
                )
        return record

    def get_or_create_session(self, session_id: str, owner_username: str) -> SessionConversationState:
        with self._lock:
            state = self._sessions.get(session_id)
            if state is None:
                state = SessionConversationState(session_id=session_id, owner_username=owner_username)
                self._sessions[session_id] = state
            elif state.owner_username != owner_username:
                # Never allow cross-user session hijacking
                raise ResultAccessDeniedError(f"Session '{session_id}' belongs to another user.")
            return state

    def update_session(
        self,
        session_id: str,
        owner_username: str,
        user_question: str,
        assistant_answer: str,
        report_id: str | None = None,
        report_name: str | None = None,
        circle: str | None = None,
        domain: str | None = None,
        result_id: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            state = self._sessions.get(session_id)
            if state is None:
                state = SessionConversationState(session_id=session_id, owner_username=owner_username)
                self._sessions[session_id] = state
            state.messages.append({"role": "user", "content": user_question})
            state.messages.append({"role": "assistant", "content": assistant_answer})
            if len(state.messages) > 40:
                state.messages = state.messages[-40:]
            if report_id is not None:
                state.last_report_id = report_id
            if report_name is not None:
                state.last_report_name = report_name
            if circle is not None:
                state.last_circle = circle
            if domain is not None:
                state.last_domain = domain
            if result_id is not None:
                state.last_result_id = result_id
            if filters is not None:
                state.last_filters = dict(filters)
            state.updated_at = time.time()


default_result_store = ResultStore()
