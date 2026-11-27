"""Chat (conversation) routes: each logged-in user's own chats and short-term memory.

Every route needs the NETIQ login session (src/security/netiq_login.py). After 30 minutes
without activity that session ends and these routes answer 401; the chats stay saved and can
be opened again after logging in. The Streamlit UI (ui/streamlit) uses these routes.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.orchestrator.chat_service import default_chat_service
from src.schemas.chat import ChatRequest
from src.security import netiq_login
from src.security.circle_access import UnauthorizedCircleError
from src.session import chat_store, identity
from src.session.chat_summary import summarise_left_chats
from src.session.history_policy import NO_HISTORY, history_for_question
from src.session.identity import SessionUser, circles_in_text, current_user, normalize_circle

log = logging.getLogger(__name__)


class MessageIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="The user's question")
    circle: str | None = Field(default=None, description="Circle the user picked in the UI, if any")
    domain: str | None = Field(default=None, description="Domain the user picked in the UI, if any")
    report_id: str | None = Field(default=None, description="Report the user picked in the UI, if any")
    page_size: int = Field(default=50, ge=1, le=500, description="Rows in the first page of a table answer")


def _not_found() -> HTTPException:
    return HTTPException(404, "Chat not found.")


async def start_session_from_netiq(request: Request) -> dict:
    """Chatbot session for the user already logged in to NETIQ, from the browser's NETIQ cookie
    (the UI forwards it in the Cookie header). No username or password is asked."""
    try:
        found = await identity.session_from_netiq_cookie(request.headers.get("cookie"))
    except httpx.RequestError as exc:
        raise HTTPException(503, f"Cannot reach NETIQ at {netiq_login.NETIQ_LOGIN_BASE_URL}: {type(exc).__name__}") from None
    if not found:
        raise HTTPException(401, "Not logged in to NETIQ. Log in to NETIQ in this browser first.")
    session_id, login = found
    return {"session_id": session_id, "user": login}


def list_conversations(background: BackgroundTasks, user: SessionUser = Depends(current_user)) -> dict:
    # Coming back after a break: summarise chats quiet for longer than the login idle timeout.
    quiet = datetime.now(timezone.utc) - timedelta(seconds=netiq_login.SESSION_IDLE_TIMEOUT)
    background.add_task(summarise_left_chats, user.username, quiet_since=quiet.isoformat(timespec="microseconds"))
    return {"username": user.username, "conversations": chat_store.list_conversations(user.username)}


def create_conversation(background: BackgroundTasks, user: SessionUser = Depends(current_user)) -> dict:
    background.add_task(summarise_left_chats, user.username)  # the chat the user just left
    return {"conversation_id": chat_store.create_conversation(user.username)}


def get_conversation(conversation_id: str, user: SessionUser = Depends(current_user)) -> dict:
    try:
        messages = chat_store.get_messages(user.username, conversation_id)
        state = chat_store.get_state(user.username, conversation_id)
    except chat_store.ConversationNotFound:
        raise _not_found() from None
    return {"conversation_id": conversation_id, "state": state, "messages": [asdict(m) for m in messages]}


async def send_message(conversation_id: str, body: MessageIn, background: BackgroundTasks,
                       user: SessionUser = Depends(current_user)) -> dict:
    try:
        previous = chat_store.recent_messages(user.username, conversation_id)
    except chat_store.ConversationNotFound:
        raise _not_found() from None
    background.add_task(summarise_left_chats, user.username, skip=conversation_id)  # chats the user moved away from

    history = history_for_question(body.question, previous)
    used = history != NO_HISTORY
    chat_store.add_message(user.username, conversation_id, "user", body.question)
    # Long-term memory hint only; access is still decided by the user's circles.
    # A circle picked in the box and named in the question counts once.
    circles = list(dict.fromkeys(([normalize_circle(body.circle)] if body.circle else []) + circles_in_text(body.question)))
    if circles:
        chat_store.record_keywords(user.username, {"circle": circles})

    # The orchestrator keeps its own state per chat (last report, circle, result) under this chat's id.
    # ponytail: `history` is worked out and shown, but the orchestrator does not take it yet;
    # pass it once its prompt has a place for it.
    filters = {k: v for k, v in (("circle", body.circle), ("domain", body.domain), ("report_id", body.report_id)) if v}
    request = ChatRequest(session_id=conversation_id, query=body.question, circle=body.circle, filters=filters,
                          pagination={"page": 0, "size": body.page_size}, user_id=user.username)
    try:
        reply = await default_chat_service.process_chat(request=request, user=user.user_context())
    except (PermissionError, UnauthorizedCircleError) as err:
        _save_failure(user, conversation_id, used, f"Sorry, I couldn't answer this question: {err}")
        raise HTTPException(403, str(err)) from err
    except Exception as err:
        log.exception("chat_answer_failed", extra={"conversation_id": conversation_id})
        _save_failure(user, conversation_id, used, "Sorry, I couldn't answer this question because of an internal error.")
        raise HTTPException(500, f"Chat orchestration error: {err}") from err

    # Length only, never the question text (it is in the chat DB already).
    log.info("chat_question", extra={"conversation_id": conversation_id, "question_chars": len(body.question),
                                     "history_used": used, "circles": circles, "intent": reply.intent,
                                     "agent": reply.agent, "status": reply.status})
    # The whole answer is saved, table rows too, so a reopened chat shows it again.
    payload = reply.model_dump(mode="json", exclude={"structured_data"})  # same rows as table.rows
    chat_store.add_message(user.username, conversation_id, "assistant", reply.answer,
                           meta={"history_used": used, "payload": payload})
    return {**payload, "conversation_id": conversation_id, "history_used": used,
            "history": history if used else "", "circles_counted": circles}


def _save_failure(user: SessionUser, conversation_id: str, used: bool, text: str) -> None:
    """Keep the failed turn in the chat; history_policy leaves such answers out of later history."""
    chat_store.add_message(user.username, conversation_id, "assistant", text, meta={"history_used": used, "failed": True})
