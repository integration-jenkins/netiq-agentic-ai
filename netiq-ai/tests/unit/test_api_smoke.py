"""Smoke test: the app boots and the routes are wired."""

from fastapi.testclient import TestClient

from src.api.app import create_app

client = TestClient(create_app())


def test_main_page_and_health():
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["status"] == "ok"


def test_chat_stub():
    r = client.post("/v1/chat", json={"query": "hello"})
    assert r.status_code == 200 and r.json()["status"] == "EMPTY"


def test_unfinished_routes_return_501():
    assert client.get("/v1/metadata/reports").status_code == 501
    assert client.post("/v1/reports/query", json={"report_id": "X"}).status_code == 501
    assert client.post("/v1/export").status_code == 501


def test_every_route_in_yaml_is_registered_with_a_description():
    from src.api.app import load_api_routes

    paths = {r.path for r in client.app.routes}
    for route in load_api_routes():
        assert route["path"] in paths
        assert route["description"].strip()
