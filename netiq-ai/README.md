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

## NETIQ Login Integration

- Added `src/security/netiq_login.py` to call the NETIQ login API, store each session's user JSON, and expose login/session routes.
- Updated `src/settings/env.py` with the NETIQ backend defaults: `NETIQ_API_BASE_URL=http://localhost:6061`, `NETIQ_LOGIN_PATH=/api/login`, and `NETIQ_LOGIN_METHOD=GET`.
- Updated `app/main.py` to add the project root to Python's import path before creating the app. Start the service with `uvicorn app.main:app --reload --port 8000`.
- Updated `src/api/app.py` to register the NETIQ authentication router with the application.

## Session Management

Each logged-in NETIQ user now has their own saved chats, and a follow-up question carries the earlier part of the chat with it.

What it does

- Login session: uses the NETIQ login from `src/security/netiq_login.py`, so there is no second login. A session ends after 30 minutes without activity (`SESSION_IDLE_TIMEOUT=1800` in `.env`). After that the chat routes answer 401. The chats stay saved and open again after the next login.
- My chats: every chat belongs to one user. Another user cannot open it or write to it.
- Short-term memory (inside one chat): a question that stands on its own is sent with no history. A follow-up ("and 5G?", "aur iska vendor?", "show the same for MH") is sent with the last two questions and answers, kept short. Failed or placeholder answers are never sent as history.
- How a follow-up is spotted: for now by simple rules, not by the AI model. A message counts as a follow-up if it is 2 words or fewer, starts with words like and / also / what about / aur / phir, points back with words like it / same / previous / iska / wahi, says "this / that" + report, site, circle..., or replies to a question the assistant asked. Spotting follow-ups with the AI model will come later in the Entity Extraction and Intent Detection task.
- Long-term memory (across chats): counts which circles each user asks about, from the circle box and from the question text. A circle named in both places counts once.
- Chat summaries: when the user leaves a chat, a local model writes a one-line summary of the questions in the background (`chat_summarizer` in `configs/models.yaml`, Qwen3 4B). If Ollama is not running, the chat simply has no summary yet and everything else still works.
- Storage: one SQLite file, `data/session/chat_history.db` (change it with `CHAT_DB_PATH`). Chats not used for 30 days are deleted. Circle counts and summaries are deleted after 90 days.
- Answers: until the orchestrator is connected, every question gets a fixed reply saying the question is saved in the chat.

Routes (all need the NETIQ login session cookie or the `X-Session-ID` header)

- `GET /v1/conversations`: my chats, with their summaries.
- `POST /v1/conversations`: start a new chat.
- `GET /v1/conversations/{conversation_id}`: open a chat with all its messages.
- `POST /v1/conversations/{conversation_id}/messages`: ask a question. The reply also shows whether history was sent and which circles were counted.
- `GET /chat-demo`: a demo page to try all of this in the browser.

Files added

- `src/session/chat_store.py`: saves chats, messages, circle counts and summaries.
- `src/session/history_policy.py`: decides if a question is a follow-up and how much history goes with it.
- `src/session/identity.py`: reads the logged-in user from the NETIQ session and finds circle names in a question.
- `src/session/chat_summary.py`: writes the one-line chat summaries.
- `src/api/routes/conversations.py`: the chat routes above.
- `ui/web/chat_demo.html`: the demo page.
- New entries in `configs/api_routes.yaml` (routes), `configs/models.yaml` (`chat_summarizer` role) and `.env.example` (session settings).
- Tests: `tests/unit/test_session_memory.py` and `tests/workflow/test_conversation_api.py`.

How to try it

1. Start the NETIQ backend on port 6061 (needed for login).
2. Optional, for summaries: start Ollama with `qwen3:4b-instruct-2507` pulled.
3. Start the service: `uvicorn app.main:app --reload --port 8000`.
4. Open http://localhost:8000/chat-demo and log in with a NETIQ user.
5. Ask "how many 4G cells in Mumbai?", then "and 5G?". The second question is tagged as a follow-up, and the page shows the history that was sent with it.

Run the tests: `python -m pytest tests/unit/test_session_memory.py tests/workflow/test_conversation_api.py`
