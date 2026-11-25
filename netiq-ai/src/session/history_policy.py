"""How much of the chat goes into the prompt for a new question.

Why not always send the history
-------------------------------
Given the whole chat, a small local model carries circles and dates from earlier turns into
questions that are complete on their own ("how many sites in BR?" becomes "... in KK, last
week"), and on a CPU-only host every 600 tokens of history adds about 25 seconds.

The policy
----------
1. A question that stands on its own gets no history: same prompt and answer as a new chat.
2. A follow-up ("and 5G?", "aur iska vendor?", "show the same for MH") gets a small window:
   the last two exchanges, user turns kept, assistant turns cut short, failed answers removed.

The check leans towards "needs history": a missing follow-up is the worse mistake.
"""

from __future__ import annotations

import re
from typing import Sequence

NO_HISTORY = "(no previous messages in this conversation)"

# Openers that continue an earlier question (English and common Hinglish).
_CONTINUATION_OPENER = re.compile(
    r"^\s*(and|also|then|so|but|now|ok(ay)?|what about|how about|same (for|with|but)|what if|instead|only|"
    r"aur|phir|toh|ab|bas|sirf)\b",
    re.IGNORECASE,
)
# Words that point back at something said before.
_POINTS_BACK = re.compile(
    r"\b(it|its|them|they|their|those|these|same|above|previous|earlier|another|else|too|ones?|"
    r"iska|iski|iske|uska|uski|uske|inka|inki|inke|unka|unki|unke|wahi|wohi|yahi|usi|isi|inme|unme|"
    r"the (first|second|third|last|other) (one|ones|report|site|node|cell|circle|link))\b",
    re.IGNORECASE,
)
# "this report", "that circle", "those sites": only meaningful if an earlier turn named it.
# Hindi "is/us/in/un" are left out on purpose: they are also everyday English words.
_DEMONSTRATIVE_NOUN = re.compile(
    r"\b(this|that|these|those|ye|yeh|woh|wo)\s+"
    r"(report|site|node|cell|circle|vendor|link|hop|board|port|ip|list|table|data|one|ones|number|id)s?\b",
    re.IGNORECASE,
)
_SHORT_REPLY_WORDS = 2          # "5G?" or "yes MH" can only be an answer to something
_ASKED_A_QUESTION = re.compile(r"\?\s*$")

# Assistant turns that describe a failure: harmful as context, a small model copies them.
_FAILURE_MARKERS = (
    "not connected to the orchestrator",
    "once the answer engine is connected",  # the placeholder reply in src/api/routes/conversations.py
    "sorry, something went wrong",
    "sorry, i couldn't",
    "i couldn't find",
    "internal error",
    "is not available right now",
    "please log in",
)

_WINDOW_MESSAGES = 4            # the last two exchanges
_USER_CAP, _ASSISTANT_CAP, _MAX_CHARS = 300, 160, 1000


def is_failure_turn(content: str) -> bool:
    lowered = (content or "").lower()
    return any(marker in lowered for marker in _FAILURE_MARKERS)


def looks_like_followup(question: str, previous: Sequence = ()) -> bool:
    """True if `question` probably depends on an earlier turn of this chat."""
    text = (question or "").strip()
    if not text:
        return False
    if len(text.split()) <= _SHORT_REPLY_WORDS:
        return True
    if _CONTINUATION_OPENER.search(text) or _POINTS_BACK.search(text) or _DEMONSTRATIVE_NOUN.search(text):
        return True
    last_answer = next((m for m in reversed(previous) if m.role == "assistant"), None)
    if last_answer is not None and not is_failure_turn(last_answer.content):
        # The assistant asked something (a clarification): this message is the reply.
        if last_answer.meta.get("pending_question") or _ASKED_A_QUESTION.search(last_answer.content.strip()):
            return True
    return False


def _compact(content: str, cap: int) -> str:
    flat = " ".join((content or "").split())
    return flat if len(flat) <= cap else flat[:cap].rstrip() + "..."


def render_followup_history(messages: Sequence) -> str:
    """The last two exchanges, short, with failed answers removed."""
    lines = []
    for m in list(messages)[-_WINDOW_MESSAGES:]:
        if m.role == "user":
            lines.append(f"User: {_compact(m.content, _USER_CAP)}")
        elif not is_failure_turn(m.content):
            lines.append(f"Assistant: {_compact(m.content, _ASSISTANT_CAP)}")
    if not lines:
        return NO_HISTORY
    text = "\n".join(lines)
    return text if len(text) <= _MAX_CHARS else "...\n" + text[-_MAX_CHARS:]


def history_for_question(question: str, messages: Sequence) -> str:
    """The chat text to put in the prompt for THIS question (NO_HISTORY for standalone ones)."""
    if not messages or not looks_like_followup(question, messages):
        return NO_HISTORY
    return render_followup_history(messages)
