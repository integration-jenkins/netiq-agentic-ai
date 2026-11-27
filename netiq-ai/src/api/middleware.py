"""HTTP middleware: a request ID for every request and one log line when it is answered.

The ID is the caller's X-Correlation-ID header when that is a plain short value, else a new
one. It is on every log line written while the request runs (also in background tasks it
starts), goes back in the X-Correlation-ID response header, and goes on to the NETIQ Java APIs.

When the response has gone out, api.log gets one "request_done" line (route, status, time
taken, user) and audit.log gets logins, logouts and refused requests. A crash is logged once
with its stack trace and answered with a 500 that carries the request ID.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid

from src.observability.audit import audit_log
from src.observability.correlation import REQUEST

log = logging.getLogger(__name__)

_SAFE_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")  # anything else from the caller is replaced (log injection)
_LOGIN_PATHS = {"/auth/loginApi", "/api/login", "/v1/session/netiq"}
_LOGOUT_PATHS = {"/auth/logout"}


class RequestLogMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        incoming = dict(scope["headers"]).get(b"x-correlation-id", b"").decode("latin-1")
        rid = incoming if _SAFE_ID.fullmatch(incoming) else uuid.uuid4().hex
        ctx = {"request_id": rid, "user": None}
        token = REQUEST.set(ctx)
        start = time.perf_counter()
        status = None

        async def send_and_log(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [*message.get("headers", []), (b"x-correlation-id", rid.encode())]
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                _answered(scope, status, start, ctx["user"])

        try:
            await self.app(scope, receive, send_and_log)
        except Exception:
            log.exception("unhandled_error", extra={"method": scope["method"], "route": _route(scope)})
            if status is not None:  # the response had already started: nothing else can be sent
                raise
            body = json.dumps({"detail": "Internal server error", "request_id": rid}).encode()
            await send_and_log({"type": "http.response.start", "status": 500,
                                "headers": [(b"content-type", b"application/json"),
                                            (b"content-length", str(len(body)).encode())]})
            await send_and_log({"type": "http.response.body", "body": body})
        finally:
            REQUEST.reset(token)


def _route(scope) -> str:
    """The route template (/v1/conversations/{conversation_id}), not the raw path with IDs in it."""
    return getattr(scope.get("route"), "path", None) or scope["path"]


def _answered(scope, status: int, start: float, user: str | None) -> None:
    fields = {"method": scope["method"], "route": _route(scope), "status": status,
              "duration_ms": round((time.perf_counter() - start) * 1000, 1), "user": user}
    log.log(logging.WARNING if status >= 500 else logging.INFO, "request_done", extra=fields)

    who = {"route": fields["route"], "status": status, "user": user,
           "client_ip": (scope.get("client") or ("-",))[0]}
    if scope["path"] in _LOGIN_PATHS:
        audit_log.info("login_success" if status < 400 else "login_failed", extra=who)
    elif scope["path"] in _LOGOUT_PATHS:
        audit_log.info("logout", extra=who)
    elif status in (401, 403):
        audit_log.info("access_denied", extra=who)
