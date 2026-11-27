"""Central logging set-up: one config, a JSON file per component, the request ID on every line.

configs/logging.yaml decides which file each part of the code writes to, the way log4j2.xml or
logback.xml does in Java. Code never opens log files itself; it only does:

    log = logging.getLogger(__name__)
    log.info("llm_call", extra={"model": model, "latency_ms": 812})

The message is the event name and `extra` holds the details. Each line in logs/ is one JSON
object: timestamp, level, module, event, request_id, then the extra fields, plus error_type,
error and stack_trace when an exception is logged (log.exception(...)).

Passwords, tokens and cookies are masked before anything is written, in files and on screen
(see redact()). Still, never log request bodies, headers or full LLM prompts.

Settings (environment): LOG_DIR (default: logs/ in the project), LOG_LEVEL (default INFO).
"""

from __future__ import annotations

import json
import logging
import logging.config
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.observability.correlation import request_id
from src.settings.env import settings
from src.settings.loader import load_yaml_file

REDACTED = "[REDACTED]"

# Header-style names: everything after them is a credential ("Authorization: Bearer x", "Cookie: a=1; b=2").
_HEADER_VALUE = re.compile(
    r"(?i)\b(authorization|proxy-authorization|cookie|set-cookie|x-session-id|x-netiq-api-key)"
    r"([\"']?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\r\n]*)"
)
# key=value and "key": "value" pairs whose key names a secret: password=..., access_token: ...
# The key must END with the secret word, so "Tokens=85" or "max_tokens=60" stay readable.
_KEY_VALUE = re.compile(
    r"(?i)\b([\w-]*?(?:password|passwd|pwd|secret|token|jwt|api[_-]?key|session[_-]?id|jsessionid|netiq_session))\b"
    r"([\"']?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s&,;\"'}\]]+)"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[\w.~+/=-]+")
_URL_USERINFO = re.compile(r"(?<=://)[^/\s:@]+:[^/\s@]+@")
# Field names in `extra` whose value is always masked.
_SECRET_FIELD = re.compile(
    r"(?i)^(.*[_-])?(password|passwd|pwd|secret|token|jwt|api[_-]?key|authorization|cookie|"
    r"session[_-]?id|jsessionid|netiq_session)$"
)

# Attributes every LogRecord has; anything else on a record came from `extra`.
_STANDARD = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime", "color_message"}
_CORE = ("timestamp", "level", "module", "event", "request_id")


def redact(text: str) -> str:
    """Mask passwords, tokens, cookies and session IDs in free text."""
    text = _HEADER_VALUE.sub(lambda m: f"{m[1]}{m[2]}{REDACTED}", text)
    text = _KEY_VALUE.sub(lambda m: f"{m[1]}{m[2]}{REDACTED}", text)
    text = _BEARER.sub(f"Bearer {REDACTED}", text)
    return _URL_USERINFO.sub(f"{REDACTED}@", text)


def _scrub(key: str, value: Any) -> Any:
    if _SECRET_FIELD.match(key):
        return REDACTED
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: _scrub(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_scrub("", v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    """One JSON object per line, secrets masked."""

    def entry(self, record: logging.LogRecord) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "module": record.name,
            "event": redact(record.getMessage()),
            "request_id": request_id(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD:
                entry.setdefault(key, _scrub(key, value))  # the core fields above always win
        if record.exc_info and record.exc_info[0]:
            entry["error_type"] = record.exc_info[0].__name__
            entry["error"] = redact(str(record.exc_info[1]))
            entry["stack_trace"] = redact(self.formatException(record.exc_info))
        return entry

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(self.entry(record), ensure_ascii=False, default=lambda v: redact(str(v)))


class ConsoleFormatter(JsonFormatter):
    """The same fields as one readable line for the terminal."""

    def format(self, record: logging.LogRecord) -> str:
        e = self.entry(record)
        details = " ".join(f"{k}={v}" for k, v in e.items() if k not in _CORE and k != "stack_trace")
        line = f"{e['timestamp'][11:23]} {e['level']:<7} [{(e['request_id'] or '-')[:8]}] {e['module']}: {e['event']} {details}"
        return line.rstrip() + (f"\n{e['stack_trace']}" if "stack_trace" in e else "")


def setup_logging() -> None:
    """Apply configs/logging.yaml. Calling it again replaces the handlers, so lines never double up."""
    config = load_yaml_file(settings.config_dir / "logging.yaml")
    log_dir = Path(os.getenv("LOG_DIR") or settings.project_root / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    for handler in config["handlers"].values():
        if "filename" in handler:
            handler["filename"] = str(log_dir / handler["filename"])
    config["root"]["level"] = os.getenv("LOG_LEVEL", config["root"].get("level", "INFO")).upper()
    logging.config.dictConfig(config)
