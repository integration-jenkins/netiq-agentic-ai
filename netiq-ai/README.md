# NetIQ Agentic AI

Starter project structure for the NetIQ Agentic AI chatbot.

## Top-level layout

- `app/`: Agent implementations, orchestration workflow and LLM application logic.
- `src/`: API, settings, schemas, observability, sessions, tools, adapters and security.
- `configs/`: Version-controlled YAML policies and report metadata.
- `knowledge_base/`: Telecom glossary, business rules, report documentation and SOPs.
- `data/`: Knowledge assets, indexes, snapshots and fixtures.
- `integration/`: Java gateway, React panel and generated OpenAPI contract.
- `tests/`: Unit, workflow, end-to-end, security, failure and benchmark tests.

## Architectural boundaries

1. `src/adapters/` is the only external-I/O boundary.
2. `src/tools/data_extraction/` performs deterministic operations and must not call an LLM.
3. `src/schemas/` contains shared contracts; keep dependencies minimal and stable.
4. `configs/allowed_apis.yaml` defines the exact approved HTTP method/path allow-list. The NETIQ HTTP adapter must enforce it.
5. Keep secrets out of version-controlled YAML; use environment variables or an approved secret provider.

This archive is a scaffold: implementation files are placeholders, not working application logic.

---
## Python service setup update - FastAPI skeleton, config, health endpoint.
What I added or changed

- `app/main.py`: creates the app. Start it with uvicorn app.main:app --reload --port 8000.
- `src/api/app.py`: builds the app, includes the routers, and serves /.
- `src/api/routes/`: health.py, chat.py, reports.py, metadata.py and export.py, each a few lines.
- `ui/web/`: an empty folder for the UI. If it contains an index.html, / serves it. Otherwise / shows a one-line - placeholder.
- `requirements.txt`: now lists the dependencies.
- `tests/unit/test_api_smoke.py`: one small test file that checks the routes are wired.

What each route does today

- `GET /` serves the UI placeholder.
- `GET /` health returns {"status": "ok", "mode": "MOCK"}.
- `POST /v1/chat` returns a placeholder answer, using your existing ChatRequest and ChatResponse.
- `GET /v1/metadata/reports` and `/v1/metadata/reports/{id}`, `POST /v1/reports/query` and `POST /v1/export` return 501. 
Each has a TODO naming the existing code to wire it to.

