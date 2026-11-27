"""Request ID (correlation ID) of the request being served.

The HTTP middleware (src/api/middleware.py) opens one context per request. Every log line
reads the request ID from here, and the NETIQ HTTP client sends it on to the Java APIs in the
X-Correlation-ID header, so one ID follows a question through every log file.
"""

from __future__ import annotations

from contextvars import ContextVar

# A dict and not a plain string: sync routes run in a worker thread with a copy of the context,
# and set_user() there must still reach the middleware that writes the request line.
REQUEST: ContextVar[dict | None] = ContextVar("netiq_request", default=None)


def request_id() -> str | None:
    """ID of the request being served, or None outside a request (start-up, scripts)."""
    ctx = REQUEST.get()
    return ctx["request_id"] if ctx else None


def set_user(username: str) -> None:
    """Remember who made this request; shown on its request line and in audit.log."""
    ctx = REQUEST.get()
    if ctx is not None:
        ctx["user"] = username
