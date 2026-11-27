"""Monitoring summary: one day's numbers, read from the JSON log files.

    python -m src.observability.metrics              # today
    python -m src.observability.metrics 2026-11-25   # another day

Requests, server errors, refused requests and response times come from api.log; LLM calls,
time and tokens from llm.log; NETIQ API calls from tools.log. Alerts and health checks on the
server are a separate, later task; summary() returns a dict so they can reuse it.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

from src.settings.env import settings


def _entries(log_dir: Path, name: str, event: str, day: str) -> list[dict[str, Any]]:
    """One day's `event` lines of <name>.log: the live file plus that day's rotated file."""
    found = []
    for path in (log_dir / f"{name}.log.{day}", log_dir / f"{name}.log"):
        if not path.is_file():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue  # a half-written last line
                if entry.get("event") == event and entry.get("timestamp", "").startswith(day):
                    found.append(entry)
    return found


def _avg(values: list[float]) -> int | None:
    return round(mean(values)) if values else None


def summary(day: str | None = None, log_dir: Path | None = None) -> dict[str, Any]:
    day = day or date.today().isoformat()
    log_dir = log_dir or Path(os.getenv("LOG_DIR") or settings.project_root / "logs")
    requests = _entries(log_dir, "api", "request_done", day)
    llm = _entries(log_dir, "llm", "llm_call", day)
    netiq = _entries(log_dir, "tools", "netiq_api_call", day)

    times = sorted(e["duration_ms"] for e in requests)
    slowest = max(requests, key=lambda e: e["duration_ms"], default=None)
    llm_ok = [e for e in llm if e.get("status") == "ok"]
    return {
        "day": day,
        "requests": len(requests),
        "server_errors": sum(e["status"] >= 500 for e in requests),
        "refused": sum(e["status"] in (401, 403) for e in requests),
        "avg_ms": _avg(times),
        "p95_ms": times[int(0.95 * (len(times) - 1))] if times else None,
        "slowest": {"route": slowest["route"], "ms": slowest["duration_ms"]} if slowest else None,
        "llm_calls": len(llm),
        "llm_failed": len(llm) - len(llm_ok),
        "llm_avg_ms": _avg([e["latency_ms"] for e in llm_ok]),
        "llm_avg_tokens_in": _avg([e["tokens_in"] for e in llm_ok]),
        "llm_avg_tokens_out": _avg([e["tokens_out"] for e in llm_ok]),
        "llm_by_model": dict(Counter(e["model"] for e in llm)),
        "netiq_api_calls": len(netiq),
        "netiq_api_failed": sum(e.get("status") != "ok" for e in netiq),
        "netiq_api_avg_ms": _avg([e["latency_ms"] for e in netiq]),
    }


def _print(s: dict[str, Any]) -> None:
    print(f"Monitoring summary for {s['day']}")
    print(f"Requests:      {s['requests']} ({s['server_errors']} server errors, {s['refused']} refused)")
    if s["requests"]:
        print(f"Response time: average {s['avg_ms']} ms, 95% under {s['p95_ms']} ms, "
              f"slowest {s['slowest']['ms']} ms ({s['slowest']['route']})")
    print(f"LLM:           {s['llm_calls']} calls ({s['llm_failed']} failed)", end="")
    if s["llm_avg_ms"] is not None:
        print(f", average {s['llm_avg_ms']} ms, about {s['llm_avg_tokens_in']} tokens in / "
              f"{s['llm_avg_tokens_out']} out", end="")
    print("".join(f"\n  {model}: {n} calls" for model, n in s["llm_by_model"].items()))
    print(f"NETIQ API:     {s['netiq_api_calls']} calls ({s['netiq_api_failed']} failed)"
          + (f", average {s['netiq_api_avg_ms']} ms" if s["netiq_api_avg_ms"] is not None else ""))


if __name__ == "__main__":
    _print(summary(sys.argv[1] if len(sys.argv) > 1 else None))
