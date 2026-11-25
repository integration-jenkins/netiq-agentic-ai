"""Chat (conversation) routes: each logged-in user's own chats and short-term memory.

Every route needs the NETIQ login session (src/security/netiq_login.py). After 30 minutes
without activity that session ends and these routes answer 401; the chats stay saved and can
be opened again after logging in.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.api.routes.ui import UI_DIR
from src.security import netiq_login
from src.session import chat_store
from src.session.chat_summary import summarise_left_chats
from src.session.history_policy import NO_HISTORY, history_for_question
from src.session.identity import SessionUser, circles_in_text, current_user, normalize_circle

# ponytail: fixed reply until the orchestrator is connected; it will get the question,
# the history from history_for_question, the user and the chat state.
NOT_CONNECTED = ("Your question is saved in this chat. Answers from NETIQ data will show here "
                 "once the answer engine is connected.")


class MessageIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="The user's question")
    circle: str | None = Field(default=None, description="Circle the user picked in the UI, if any")


def _not_found() -> HTTPException:
    return HTTPException(404, "Chat not found.")


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


def send_message(conversation_id: str, body: MessageIn, background: BackgroundTasks,
                 user: SessionUser = Depends(current_user)) -> dict:
    try:
        previous = chat_store.recent_messages(user.username, conversation_id)
    except chat_store.ConversationNotFound:
        raise _not_found() from None
    background.add_task(summarise_left_chats, user.username, skip=conversation_id)  # chats the user moved away from

    history = history_for_question(body.question, previous)
    chat_store.add_message(user.username, conversation_id, "user", body.question)
    # Long-term memory hint only; access is still decided by the user's circles.
    # A circle picked in the box and named in the question counts once.
    circles = list(dict.fromkeys(([normalize_circle(body.circle)] if body.circle else []) + circles_in_text(body.question)))
    if circles:
        chat_store.record_keywords(user.username, {"circle": circles})

    answer = NOT_CONNECTED
    used = history != NO_HISTORY
    chat_store.add_message(user.username, conversation_id, "assistant", answer, meta={"history_used": used})
    return {"conversation_id": conversation_id, "answer": answer, "history_used": used,
            "history": history if used else "", "circles_counted": circles}


def chat_demo_page() -> FileResponse:
    """Demo page for session management: login, my chats, follow-up history."""
    return FileResponse(UI_DIR / "chat_demo.html", headers={"Cache-Control": "no-cache"})  # always the latest page
