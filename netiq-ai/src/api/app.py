"""FastAPI application factory and composition root.

Routes are declared in configs/api_routes.yaml and registered here.
"""

from importlib import import_module

from fastapi import FastAPI

from src.settings.env import settings
from src.settings.loader import ConfigurationError, load_yaml_file


def load_api_routes() -> list[dict]:
    data = load_yaml_file(settings.config_dir / "api_routes.yaml")
    routes = data.get("api_routes") if isinstance(data, dict) else None
    if not routes:
        raise ConfigurationError("configs/api_routes.yaml must define 'api_routes'")
    return routes


def create_app() -> FastAPI:
    app = FastAPI(title="NetIQ Agentic AI", version="0.1.0")

    seen: set[tuple[str, str]] = set()
    for route in load_api_routes():
        key = (route["method"].upper(), route["path"])
        if key in seen:
            raise ConfigurationError(f"Duplicate API route in api_routes.yaml: {key}")
        seen.add(key)

        module_path, _, func_name = route["handler"].partition(":")
        try:
            handler = getattr(import_module(module_path), func_name)
        except (ImportError, AttributeError) as exc:
            raise ConfigurationError(f"Route '{route['id']}': cannot load handler '{route['handler']}'") from exc

        summary = route["summary"]
        if route.get("status") == "stub":
            summary += " [not implemented]"
        app.add_api_route(
            route["path"],
            handler,
            methods=[route["method"].upper()],
            tags=[route["tag"]],
            summary=summary,
            description=route.get("description"),
            include_in_schema=route.get("in_schema", True),
            name=route["id"],
        )
    return app
