"""Logging and monitoring (task 1.7): request ID across files, no secrets, rotation, summary."""

import json
import logging
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.llms.llm_client import default_llm_client
from src.adapters.llm.provider import OllamaProvider
from src.adapters.netiq_http.client import NetIQHttpClient
from src.api.app import create_app
from src.observability import metrics
from src.observability.logging import redact, setup_logging
from src.schemas.reports import ReportQuery
from src.settings.env import ApiMode

SECRET = "S3cret-pass!42"


def fake_ollama(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"response": "REPORT", "done": True, "eval_count": 7,
                                     "eval_duration": 100_000_000, "prompt_eval_count": 42})


@pytest.fixture
def app_and_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setattr(default_llm_client, "provider", OllamaProvider(transport=httpx.MockTransport(fake_ollama)))
    return TestClient(create_app(), raise_server_exceptions=False), tmp_path


def lines(log_dir, name, event=None):
    path = log_dir / f"{name}.log"
    found = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
    return [e for e in found if event is None or e["event"] == event]


@pytest.mark.parametrize("text", [
    f"HTTP Request: GET http://localhost:6061/api/login?username=u&password={SECRET} 200",
    f"{{'username': 'u', 'password': '{SECRET}'}}",
    f'{{"access_token": "{SECRET}"}}',
    f"Authorization: Bearer {SECRET}",
    f"Cookie: JSESSIONID=1; netiq_session={SECRET}",
    f"X-Session-ID={SECRET}",
    f"http://admin:{SECRET}@host/path",
])
def test_secrets_are_masked(text):
    assert SECRET not in redact(text) and "[REDACTED]" in redact(text)


def test_numbers_that_only_look_like_tokens_stay():
    assert redact("Tokens=85 tokens_in=410 max_tokens=60") == "Tokens=85 tokens_in=410 max_tokens=60"


def test_one_request_id_follows_the_question_into_every_file(app_and_logs):
    client, log_dir = app_and_logs
    resp = client.post("/v1/inference", json={"prompt": "which report?"}, headers={"X-Correlation-ID": "trace-123"})
    assert resp.status_code == 200 and resp.headers["X-Correlation-ID"] == "trace-123"

    [done] = lines(log_dir, "api", "request_done")
    assert (done["request_id"], done["route"], done["status"]) == ("trace-123", "/v1/inference", 200)
    [llm] = lines(log_dir, "llm")
    assert llm["request_id"] == "trace-123" and llm["status"] == "ok"
    assert (llm["tokens_in"], llm["tokens_out"]) == (42, 7) and "which report?" not in json.dumps(llm)


def test_a_failed_llm_call_is_logged_and_counted(app_and_logs, monkeypatch):
    client, log_dir = app_and_logs

    def ollama_down(request):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(default_llm_client, "provider", OllamaProvider(transport=httpx.MockTransport(ollama_down)))
    assert client.post("/v1/inference", json={"prompt": "hi"}).status_code == 503
    [llm] = lines(log_dir, "llm")
    assert (llm["status"], llm["error_type"]) == ("error", "OllamaConnectionError")
    assert {e["event"] for e in lines(log_dir, "errors")} == {"llm_call", "request_done"}  # copied to errors.log
    s = metrics.summary(log_dir=log_dir)
    assert (s["llm_failed"], s["server_errors"]) == (1, 1)


@pytest.mark.anyio
async def test_netiq_api_calls_go_to_tools_log(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    setup_logging()
    client = NetIQHttpClient(mode=ApiMode.MOCK)
    await client.execute_report_query(ReportQuery(report_id="RAN_CELL_4G", circle="BR", page=0, size=50), ["BR"])
    with pytest.raises(Exception):  # a circle the user may not see
        await client.execute_report_query(ReportQuery(report_id="RAN_CELL_4G", circle="MH", page=0, size=50), ["BR"])
    await client.close()

    ok, failed = lines(tmp_path, "tools", "netiq_api_call")
    assert (ok["status"], ok["rows"], ok["report_id"]) == ("ok", 2, "RAN_CELL_4G")
    assert (failed["status"], failed["error_type"]) == ("error", "UnauthorizedCircleError")


def test_an_odd_incoming_id_is_replaced(app_and_logs):
    client, _ = app_and_logs
    sent = "bad id " + "x" * 80
    assert client.get("/health", headers={"X-Correlation-ID": sent}).headers["X-Correlation-ID"] != sent


def test_secrets_never_reach_a_file_and_a_crash_keeps_its_stack_trace(app_and_logs):
    client, log_dir = app_and_logs

    def crash():
        logging.getLogger("src.tools.demo").info("calling", extra={"password": SECRET, "headers": {"Authorization": f"Bearer {SECRET}"}})
        logging.getLogger("httpx").warning(f"HTTP Request: GET http://x/api/login?username=u&password={SECRET}")
        raise RuntimeError(f"backend said password={SECRET}")

    client.app.add_api_route("/crash", crash)
    resp = client.get("/crash")
    rid = resp.headers["X-Correlation-ID"]
    assert resp.status_code == 500 and resp.json()["request_id"] == rid

    [err] = lines(log_dir, "errors", "unhandled_error")
    assert err["request_id"] == rid and err["error_type"] == "RuntimeError" and "in crash" in err["stack_trace"]
    assert lines(log_dir, "tools", "calling")[0]["request_id"] == rid  # also from a sync route's worker thread
    assert all(SECRET not in f.read_text(encoding="utf-8") for f in log_dir.iterdir())


def test_setting_up_twice_still_writes_each_line_once(app_and_logs):
    client, log_dir = app_and_logs
    create_app()  # a second set-up, as on a reload
    client.get("/health")
    assert len(lines(log_dir, "api", "request_done")) == 1


def test_files_rotate_at_midnight_and_old_ones_are_deleted(app_and_logs):
    client, log_dir = app_and_logs
    handlers = {h.baseFilename.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]: h
                for name in ("src.api", "netiq.audit") for h in logging.getLogger(name).handlers if hasattr(h, "baseFilename")}
    assert handlers["api.log"].when == "MIDNIGHT" and handlers["api.log"].backupCount == 30
    assert handlers["audit.log"].backupCount == 90

    for n in range(1, 41):  # 40 old days on disk
        (log_dir / f"api.log.{date(2026, 10, 1) + timedelta(days=n)}").write_text("")
    client.get("/health")
    handlers["api.log"].doRollover()
    assert len(list(log_dir.glob("api.log.*"))) == 30


def test_monitoring_summary_counts_requests_refusals_and_llm_calls(app_and_logs):
    client, log_dir = app_and_logs
    client.get("/v1/conversations")  # not logged in -> 401, and an audit line
    client.post("/v1/inference", json={"prompt": "hi"})
    assert lines(log_dir, "audit")[0]["event"] == "access_denied"

    s = metrics.summary(log_dir=log_dir)
    assert (s["requests"], s["refused"], s["server_errors"]) == (2, 1, 0)
    assert (s["llm_calls"], s["llm_failed"], s["llm_avg_tokens_in"], s["llm_avg_tokens_out"]) == (1, 0, 42, 7)
