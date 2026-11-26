"""Smoke test: the app boots and the routes are wired."""

from fastapi.testclient import TestClient

from src.api.app import create_app

client = TestClient(create_app())


def test_main_page_and_health():
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["status"] == "ok"


def test_chat_endpoint_wired():
    r = client.post("/v1/chat", json={"query": "Show 4G cell inventory for Delhi", "circle": "DL", "user_permitted_circles": ["DL"]})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("SUCCESS", "EMPTY")
    assert body["report_id"] == "RAN_CELL_4G"


def test_implemented_metadata_and_query_routes():
    assert client.get("/v1/metadata/reports").status_code == 200
    assert client.get("/v1/metadata/circles").status_code == 200
    assert client.get("/v1/metadata/domains").status_code == 200
    assert client.get("/v1/metadata/agents").status_code == 200


def test_every_route_in_yaml_is_registered_with_a_description():
    from src.api.app import load_api_routes

    paths = {getattr(r, "path", None) for r in client.app.routes}
    for route in load_api_routes():
        assert route["path"] in paths
        assert route["description"].strip()
