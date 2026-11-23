"""
netiq_login.py - single-file login + session store for NETIQ.

What it does
------------
1. Calls the NETIQ backend:  http://localhost:6061/api/login?username=...&password=...
2. Takes the JSON response (role, permissions, name, id, circleList, username)
3. Stores it in the module-level variable `user_info`, one entry per logged-in
   user session, so many users can be logged in at the same time.

    user_info = {
        "<session_id>": {"user": {...login JSON...}, "last_seen": <monotonic secs>},
        ...
    }

Use `get_user_info(session_id)` to read a user's login JSON; it also applies the idle timeout.

Requires:  pip install httpx        (FastAPI is optional, only for the bundled router)

Config (environment variables)
------------------------------
NETIQ_LOGIN_BASE_URL  optional; falls back to NETIQ_API_BASE_URL, then http://localhost:6061
NETIQ_LOGIN_PATH      default /api/login                 -> http://localhost:6061/api/login
NETIQ_LOGIN_METHOD    default GET                        GET or POST
NETIQ_API_TIMEOUT     default 15                         seconds
SESSION_IDLE_TIMEOUT  default 28800                      seconds (8 h)

Quick use
---------
    from netiq_login import login, get_user_info, has_permission, logout

    session_id, data = await login("NETIQ_ADMIN", "test123")
    get_user_info(session_id)["permissions"]        # list of {"authority": ...}
    has_permission(session_id, "NETIQ_EXPORT_REPORT")
    logout(session_id)

FastAPI use (optional) - routes exposed by `router`
---------------------------------------------------
    POST /api/login                         login (JSON body; legacy query params supported)
    POST /auth/loginApi                       login (JSON body {"username","password"})
    GET  /auth/me                             current user's login JSON (401 if not logged in)
    POST /auth/logout                         end this session only

    from fastapi import FastAPI
    from netiq_login import router
    app = FastAPI(); app.include_router(router)
"""

from __future__ import annotations

import os
import secrets
import threading
import time
from typing import Any, Iterable

import httpx
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader so NETIQ_* values in .env are honoured (os.getenv alone ignores .env)."""
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# --------------------------------------------------------------------------- config

NETIQ_LOGIN_BASE_URL = (os.getenv("NETIQ_LOGIN_BASE_URL") or os.getenv("NETIQ_API_BASE_URL") or "http://localhost:6061").rstrip("/")
NETIQ_LOGIN_PATH = os.getenv("NETIQ_LOGIN_PATH", "/api/login")
NETIQ_LOGIN_METHOD = os.getenv("NETIQ_LOGIN_METHOD", "GET").upper()
NETIQ_API_TIMEOUT = float(os.getenv("NETIQ_API_TIMEOUT", "15"))
SESSION_IDLE_TIMEOUT = float(os.getenv("SESSION_IDLE_TIMEOUT", str(8 * 3600)))

# --------------------------------------------------------------------------- store

# session_id -> {"user": <login JSON dict>, "last_seen": float}
user_info: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


# --------------------------------------------------------------------------- errors

class LoginError(Exception):
    """Base class for login failures."""


class InvalidCredentials(LoginError):
    """Backend rejected the username/password (HTTP 401/403)."""


class BackendUnavailable(LoginError):
    """Backend unreachable, timed out, or returned 5xx."""


class BadLoginResponse(LoginError):
    """Backend answered, but the body is not the expected login JSON."""


# --------------------------------------------------------------------------- parsing

def parse_login_response(payload: Any, fallback_username: str | None = None) -> dict[str, Any]:
    """Normalise the /api/login JSON. Lenient: any JSON object is accepted and stored.

    Typical shape: {"role": null|str, "permissions": [{"authority": str}], "name": str,
                    "id": str, "circleList": [str], "username": str}
    """
    if not isinstance(payload, dict):
        raise BadLoginResponse(f"Login response is not a JSON object. Got: {str(payload)[:200]!r}")
    for wrapper in ("data", "user", "result"):  # some backends wrap the payload
        if isinstance(payload.get(wrapper), dict) and "username" not in payload:
            payload = payload[wrapper]
            break
    if "error" in payload and len(payload) <= 2 and "username" not in payload:
        raise InvalidCredentials(str(payload.get("error")))

    username = payload.get("username") or payload.get("userName") or payload.get("user_name") \
        or payload.get("name") or payload.get("id") or fallback_username
    permissions = payload.get("permissions") or payload.get("authorities") or []
    circles = payload.get("circleList") or payload.get("circles") or []
    if isinstance(permissions, str):
        permissions = [x for x in permissions.split(",") if x.strip()]
    if isinstance(circles, str):
        circles = [x for x in circles.split(",") if x.strip()]
    if not isinstance(permissions, list):
        permissions = []
    if not isinstance(circles, list):
        circles = []
    permissions = [{"authority": p} if isinstance(p, str) else p for p in permissions]

    return {
        **payload,  # keep every field the backend sent
        "username": str(username) if username is not None else None,
        "role": payload.get("role"),
        "permissions": [
            {"authority": str(p["authority"])}
            for p in permissions
            if isinstance(p, dict) and p.get("authority")
        ],
        "circleList": list(dict.fromkeys(str(c).strip().upper() for c in circles if str(c).strip())),
    }


# --------------------------------------------------------------------------- login

async def login(
    username: str,
    password: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[str, dict[str, Any]]:
    """Call the backend login API, store the JSON in `user_info`, return (session_id, data).

    Nothing is stored if the login fails. `transport` is only for tests.
    """
    if NETIQ_LOGIN_METHOD not in ("POST", "GET"):
        raise LoginError(f"Unsupported NETIQ_LOGIN_METHOD: {NETIQ_LOGIN_METHOD}")

    # Different backends expect credentials differently; try the configured way first,
    # then fall back if the backend says "wrong method / bad request / unsupported type".
    attempts = [(NETIQ_LOGIN_METHOD, "query")]
    for extra in (("GET", "query"), ("POST", "json"), ("POST", "form")):
        if extra not in attempts:
            attempts.append(extra)

    resp = None
    try:
        async with httpx.AsyncClient(
            base_url=NETIQ_LOGIN_BASE_URL, timeout=NETIQ_API_TIMEOUT, transport=transport
        ) as http:
            for method, mode in attempts:
                kwargs: dict[str, Any] = {}
                creds = {"username": username, "password": password}
                if mode == "query":
                    kwargs["params"] = creds
                elif mode == "json":
                    kwargs["json"] = creds
                else:
                    kwargs["data"] = creds
                resp = await http.request(
                    method, NETIQ_LOGIN_PATH, headers={"Accept": "application/json"}, **kwargs
                )
                if resp.status_code not in (400, 403, 404, 405, 415) or (resp.status_code == 403 and (method, mode) == attempts[-1]):
                    break
    except httpx.RequestError as exc:  # timeout, DNS, connection refused...
        raise BackendUnavailable(
            f"Cannot reach NETIQ backend at {NETIQ_LOGIN_BASE_URL}{NETIQ_LOGIN_PATH}: {type(exc).__name__}"
        ) from None

    snippet = (resp.text or "")[:300]
    if 300 <= resp.status_code < 400:
        raise LoginError(
            f"NETIQ backend redirected (HTTP {resp.status_code}) to {resp.headers.get('location')!r}. "
            "Usually a wrong login path/context path, or Spring Security form-login. "
            "Use GET /auth/debug/probe to find the right path."
        )
    if resp.status_code == 404 and "html" in resp.headers.get("content-type", "").lower():
        raise LoginError(
            f"Tomcat 404 for {NETIQ_LOGIN_BASE_URL}{NETIQ_LOGIN_PATH} - the app is probably deployed under a "
            "context path (e.g. /netiq/api/login). Set NETIQ_LOGIN_PATH in .env, or use GET /auth/debug/probe."
        )
    if resp.status_code in (401, 403):
        raise InvalidCredentials(f"Invalid username or password. Backend said: {snippet}")
    if resp.status_code >= 500:
        raise BackendUnavailable(f"NETIQ backend returned HTTP {resp.status_code}: {snippet}")
    if resp.status_code >= 400:
        raise LoginError(
            f"NETIQ backend returned HTTP {resp.status_code} for {NETIQ_LOGIN_BASE_URL}{NETIQ_LOGIN_PATH}: {snippet}"
        )
    try:
        data = parse_login_response(resp.json(), fallback_username=username)
    except ValueError:
        raise BadLoginResponse(f"Login response was not valid JSON. Body: {snippet!r}") from None

    return _create_session(data), data


def _create_session(data: dict[str, Any]) -> str:
    session_id = secrets.token_urlsafe(32)
    now = time.monotonic()
    with _lock:
        for sid in [s for s, r in user_info.items() if now - r["last_seen"] > SESSION_IDLE_TIMEOUT]:
            del user_info[sid]  # drop expired sessions
        user_info[session_id] = {"user": data, "last_seen": now}
    return session_id


# --------------------------------------------------------------------------- read / helpers

def get_user_info(session_id: str | None) -> dict[str, Any] | None:
    """Login JSON for this session, or None if unknown/expired. Refreshes the idle timer."""
    if not session_id:
        return None
    now = time.monotonic()
    with _lock:
        rec = user_info.get(session_id)
        if rec is None:
            return None
        if now - rec["last_seen"] > SESSION_IDLE_TIMEOUT:
            del user_info[session_id]
            return None
        rec["last_seen"] = now
        return rec["user"]


def logout(session_id: str | None) -> bool:
    """End one session only; other users stay logged in."""
    if not session_id:
        return False
    with _lock:
        return user_info.pop(session_id, None) is not None


def permission_codes(session_id: str | None) -> frozenset[str]:
    u = get_user_info(session_id)
    return frozenset(p["authority"] for p in u["permissions"]) if u else frozenset()


def has_permission(session_id: str | None, authority: str) -> bool:
    return authority in permission_codes(session_id)


def has_any_permission(session_id: str | None, authorities: Iterable[str]) -> bool:
    codes = permission_codes(session_id)
    return any(a in codes for a in authorities)


def has_all_permissions(session_id: str | None, authorities: Iterable[str]) -> bool:
    codes = permission_codes(session_id)
    return all(a in codes for a in authorities)


def has_circle(session_id: str | None, circle: str) -> bool:
    u = get_user_info(session_id)
    return bool(u) and circle.strip().upper() in u["circleList"]


# --------------------------------------------------------------------------- optional FastAPI router

try:
    from fastapi import APIRouter, Depends, HTTPException, Request, Response
    from pydantic import BaseModel
except ImportError:  # FastAPI not installed: the functions above still work
    router = None
else:
    SESSION_COOKIE = "netiq_session"
    SESSION_HEADER = "X-Session-ID"
    router = APIRouter(tags=["auth"])

    class LoginRequest(BaseModel):
        username: str
        password: str

    def _session_id(request: Request) -> str | None:
        return request.headers.get(SESSION_HEADER) or request.cookies.get(SESSION_COOKIE)

    def current_user(request: Request) -> dict[str, Any]:
        """FastAPI dependency: the login JSON for the caller's session, or 401."""
        u = get_user_info(_session_id(request))
        if u is None:
            raise HTTPException(401, "Not logged in or session expired.")
        return u

    async def _do_login(username: str, password: str, response: Response) -> dict[str, Any]:
        try:
            session_id, data = await login(username, password)
        except InvalidCredentials:
            raise HTTPException(401, "Invalid username or password.")
        except BackendUnavailable as exc:
            raise HTTPException(503, str(exc))
        except LoginError as exc:
            raise HTTPException(502, str(exc))
        response.set_cookie(
            SESSION_COOKIE, session_id, httponly=True, samesite="lax",
            max_age=int(SESSION_IDLE_TIMEOUT),
        )
        return {"session_id": session_id, "user": data}

    @router.post("/api/login")
    async def api_login(
        response: Response,
        body: LoginRequest | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> dict[str, Any]:
        """Log in with a JSON body or legacy username/password query parameters."""
        if body is not None:
            username, password = body.username, body.password
        if not username or not password:
            raise HTTPException(422, "Provide username and password.")
        return await _do_login(username, password, response)

    @router.post("/auth/loginApi")
    async def auth_login_api(body: LoginRequest, response: Response) -> dict[str, Any]:
        """POST /auth/loginApi with JSON body {"username": "...", "password": "..."}."""
        return await _do_login(body.username, body.password, response)

    @router.get("/auth/me")
    async def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        """GET /auth/me - login JSON of the caller's session (cookie or X-Session-ID), else 401."""
        return user

    @router.get("/auth/debug/user_info")
    async def debug_user_info() -> dict[str, Any]:
        """TESTING ONLY: dump the in-memory `user_info` store. Remove before production."""
        return {sid[:8] + "...": rec["user"] for sid, rec in user_info.items()}

    @router.get("/auth/debug/config")
    async def debug_config() -> dict[str, Any]:
        """TESTING ONLY: show which backend URL the login code is really using."""
        return {"login_url": f"{NETIQ_LOGIN_BASE_URL}{NETIQ_LOGIN_PATH}", "method": NETIQ_LOGIN_METHOD}

    # ------------------------------------------------------------------ session-based user info
    # The user logs in on the 6061 page. Browsers send cookies by HOSTNAME (not port), so the 6061
    # session cookie also reaches this service. We forward it to 6061 and store the JSON that comes back.
    import hashlib

    USERINFO_PATH = os.getenv("NETIQ_USERINFO_PATH", "").strip()
    TEST_USERNAME = os.getenv("NETIQ_TEST_USERNAME", "").strip()
    TEST_PASSWORD = os.getenv("NETIQ_TEST_PASSWORD", "")
    _USERINFO_CANDIDATES = [
        "/api/login", "/api/user", "/api/me", "/api/auth/me", "/api/user/info", "/api/userinfo",
        "/api/currentUser", "/api/session", "/auth/me", "/api/users/me", "/api/profile", "/api/auth/user",
    ]

    def _looks_like_user(body: Any) -> bool:
        if not isinstance(body, dict):
            return False
        inner = next((body[k] for k in ("data", "user", "result") if isinstance(body.get(k), dict)), body)
        keys = {str(k).lower() for k in inner}
        return bool(keys & {"username", "permissions", "circlelist", "authorities", "role", "roles"})

    def _store_user(key: str, data: dict[str, Any]) -> None:
        with _lock:
            user_info[key] = {"user": data, "last_seen": time.monotonic()}

    @router.get("/auth/session-info")
    async def session_info(request: Request) -> dict[str, Any]:
        """Take the logged-in user's JSON from 6061 (via the browser's 6061 session cookie) and store it in user_info."""
        cookie_header = request.headers.get("cookie", "")
        auth_header = request.headers.get("authorization", "")
        cookie_names = sorted({c.split("=", 1)[0].strip() for c in cookie_header.split(";") if "=" in c})
        fwd = {"Accept": "application/json"}
        if cookie_header:
            fwd["Cookie"] = cookie_header
        if auth_header:
            fwd["Authorization"] = auth_header

        tried: list[dict[str, Any]] = []
        found: tuple[str, Any] | None = None
        if cookie_header or auth_header:
            paths = ([USERINFO_PATH] if USERINFO_PATH else []) + [p for p in _USERINFO_CANDIDATES if p != USERINFO_PATH]
            async with httpx.AsyncClient(base_url=NETIQ_LOGIN_BASE_URL, timeout=NETIQ_API_TIMEOUT, follow_redirects=False) as http:
                for path in paths:
                    try:
                        r = await http.get(path, headers=fwd)
                    except httpx.RequestError as exc:
                        tried.append({"path": path, "error": f"{type(exc).__name__} - is 6061 running?"})
                        break
                    ctype = (r.headers.get("content-type") or "")
                    entry: dict[str, Any] = {"path": path, "status": r.status_code, "content_type": ctype,
                                             "location": r.headers.get("location")}
                    body = None
                    if r.status_code == 200 and "json" in ctype.lower():
                        try:
                            body = r.json()
                        except ValueError:
                            body = None
                        entry["body_preview"] = str(body)[:150]
                    tried.append(entry)
                    if body is not None and _looks_like_user(body):
                        found = (path, body)
                        break

        base: dict[str, Any] = {"cookies_received": cookie_names, "tried": tried}
        if found:
            data = parse_login_response(found[1])
            key = "cookie-" + hashlib.sha256(cookie_header.encode()).hexdigest()[:16]
            _store_user(key, data)
            return {"source": f"6061 session cookie via GET {found[0]}", "user": data, **base}

        if TEST_USERNAME and TEST_PASSWORD:  # optional testing fallback (set in .env)
            try:
                sid, data = await login(TEST_USERNAME, TEST_PASSWORD)
                return {"source": "TEST credentials from .env (NETIQ_TEST_USERNAME) via login API", "user": data, **base}
            except LoginError as exc:
                base["test_login_error"] = str(exc)

        if not cookie_names:
            base["message"] = (
                "No cookies reached this service. Log in at http://<same-host>:6061/login first, then reload this page. "
                "Use the SAME hostname for both (localhost vs 127.0.0.1 are different to the browser). "
                "If the 6061 app keeps its login in browser localStorage instead of a cookie, tell me and I will adapt."
            )
        else:
            base["message"] = (
                "Cookies arrived but none of the tried 6061 endpoints returned user JSON. "
                "Check 'tried' below; set NETIQ_USERINFO_PATH in .env to the right endpoint."
            )
        return {"user": None, **base}

    @router.get("/auth/debug/raw")
    async def debug_raw(username: str, password: str) -> dict[str, Any]:
        """TESTING ONLY: call the backend login and return its raw status/headers/body, unparsed."""
        async with httpx.AsyncClient(base_url=NETIQ_LOGIN_BASE_URL, timeout=NETIQ_API_TIMEOUT, follow_redirects=False) as http:
            try:
                r = await http.request(NETIQ_LOGIN_METHOD, NETIQ_LOGIN_PATH,
                                       params={"username": username, "password": password})
            except httpx.RequestError as exc:
                raise HTTPException(503, f"Cannot reach {NETIQ_LOGIN_BASE_URL}{NETIQ_LOGIN_PATH}: {type(exc).__name__}")
        try:
            body: Any = r.json()
        except ValueError:
            body = r.text[:2000]
        return {"requested": f"{NETIQ_LOGIN_METHOD} {NETIQ_LOGIN_BASE_URL}{NETIQ_LOGIN_PATH}",
                "status": r.status_code, "content_type": r.headers.get("content-type"),
                "set_cookie": r.headers.get("set-cookie"), "body": body}

    @router.get("/auth/debug/probe")
    async def debug_probe(context: str | None = None) -> list[dict[str, Any]]:
        """TESTING ONLY: try common Tomcat context paths for the login API and report each answer."""
        contexts = [context] if context else ["", "/netiq", "/NETIQ", "/netiq-api", "/netiq-backend", "/NetIQ", "/api-gateway"]
        suffixes = ["/api/login", "/login", "/api/auth/login", "/auth/login"]
        out: list[dict[str, Any]] = []
        async with httpx.AsyncClient(base_url=NETIQ_LOGIN_BASE_URL, timeout=5, follow_redirects=False) as http:
            for ctx in contexts:
                for suf in suffixes:
                    path = f"{ctx}{suf}"
                    for method in ("GET", "POST"):
                        try:
                            r = await http.request(method, path, params={"username": "probe", "password": "probe"})
                            out.append({"method": method, "url": NETIQ_LOGIN_BASE_URL + path, "status": r.status_code,
                                        "content_type": r.headers.get("content-type"),
                                        "location": r.headers.get("location"), "body": (r.text or "")[:120]})
                        except httpx.RequestError as exc:
                            out.append({"method": method, "url": NETIQ_LOGIN_BASE_URL + path, "error": type(exc).__name__})
        # most interesting first: anything that is not a plain HTML 404
        out.sort(key=lambda x: (x.get("status") == 404 and "html" in str(x.get("content_type")), x.get("status", 0)))
        return out

    @router.post("/auth/logout")
    async def logout_route(request: Request, response: Response) -> dict[str, str]:
        logout(_session_id(request))
        response.delete_cookie(SESSION_COOKIE)
        return {"status": "logged_out"}