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
- Answers: come from the orchestrator and are saved whole, table included (see "Session Management in the Streamlit UI" below).

Routes (all need the NETIQ login session cookie or the `X-Session-ID` header)

- `GET /v1/conversations`: my chats, with their summaries.
- `POST /v1/conversations`: start a new chat.
- `GET /v1/conversations/{conversation_id}`: open a chat with all its messages.
- `POST /v1/conversations/{conversation_id}/messages`: ask a question. The reply also shows whether history was sent and which circles were counted.

Files added

- `src/session/chat_store.py`: saves chats, messages, circle counts and summaries.
- `src/session/history_policy.py`: decides if a question is a follow-up and how much history goes with it.
- `src/session/identity.py`: reads the logged-in user from the NETIQ session and finds circle names in a question.
- `src/session/chat_summary.py`: writes the one-line chat summaries.
- `src/api/routes/conversations.py`: the chat routes above.
- New entries in `configs/api_routes.yaml` (routes), `configs/models.yaml` (`chat_summarizer` role) and `.env.example` (session settings).
- Tests: `tests/unit/test_session_memory.py` and `tests/workflow/test_conversation_api.py`.

How to try it: in the Streamlit UI, see "Session Management in the Streamlit UI" below. For chat summaries, start Ollama with `qwen3:4b-instruct-2507` pulled.

Run the tests: `python -m pytest tests/unit/test_session_memory.py tests/workflow/test_conversation_api.py`

## Session Management in the Streamlit UI

Session management now works in the Streamlit UI (`ui/streamlit`), the same way it worked on the old demo page, which is now removed. Answers come from the orchestrator, so a saved chat keeps the real answers with their tables.

What it does

- No login form: the chat opens for the user who is already logged in to NETIQ in the same browser. NETIQ keeps its login in a browser cookie, and the backend asks NETIQ (`GET /auth/me`) who owns it. No username or password is asked.
- Same host name: browsers share cookies by host name, not port, so open NETIQ and the chatbot with the same host name. `localhost` and `127.0.0.1` count as different.
- Not logged in to NETIQ: the page says "Log in to NETIQ first" with a link. Log in to NETIQ, then reload the chatbot page. Streamlit reads the cookies only when the page opens.
- Sidebar: who is logged in and their circles, New Conversation, and My chats: the user's saved chats, newest first, with the one-line summary and the time. Click a chat to open it again. There is no Log out button; logging out happens in NETIQ.
- New chat: it is saved when its first question is sent.
- Answers: the backend works out the follow-up history, counts the circles, asks the orchestrator for the answer, and saves the question and the whole answer (text, number cards, table rows, sources, export). The answer is the same one `/v1/chat` gives. A reopened chat shows its tables again.
- Follow-up tag: under each answer, "Follow-up, so chat history was sent" or "New question, no history sent". For the newest answer, "What the AI received as history with this question" shows the history text.
- Filters: the circle, domain and report picked in the sidebar go with the question. The circle also counts for long-term memory.
- A failed answer: the question and a short "Sorry, I couldn't answer..." reply are saved, and the error shows with a Retry button. Such replies are never sent as history.
- Session end: the chatbot session ends after 30 minutes without activity. If the user is still logged in to NETIQ, it is renewed quietly: the open chat stays, and a question that was not sent can be sent with Retry. If not, the page asks to log in to NETIQ. The chats stay saved.
- Logging out of NETIQ: the open chatbot page keeps working until it is reloaded or stays unused for 30 minutes.
- Table pages and Excel export: these work for the logged-in user. The page and export routes now also accept the NETIQ login, and an ended login gets 401. Without a login they work as before, with the API key.
- For now: the orchestrator does not use the history text yet. It keeps its own memory for each chat (last report, circle and result). The history is worked out and shown, ready for when the orchestrator uses it.
- Older tables: page buttons and export work for 1 hour after the answer, because results are kept in memory for 1 hour. After that the saved first page still shows.
- Logging: the `chat_question` line in `api.log` now also shows the route the orchestrator chose (`intent`, `agent`, `status`).

Files added or changed

- `ui/streamlit/components/login_panel.py` (new): takes the user from the NETIQ login cookie, or shows "Log in to NETIQ first".
- `ui/streamlit/app.py`: opens the chat only for a user logged in to NETIQ.
- `ui/streamlit/components/sidebar.py`: the user and My chats.
- `ui/streamlit/components/chat_panel.py`: sends each question to the saved chat and shows the follow-up tag and the history.
- `ui/streamlit/session_manager.py`: keeps the session and the open chat, and opens a saved chat.
- `ui/streamlit/api_client.py`: sends the session as the `X-Session-ID` header, and has new calls for the session and chats.
- `ui/streamlit/config.py`: `NETIQ_WEB_URL`, the NETIQ link on the "Log in to NETIQ first" message. When empty, it is this host on port 6061.
- `src/api/routes/conversations.py`: new route `POST /v1/session/netiq`, which starts a session from the NETIQ login cookie. The message route gets the answer from the orchestrator and saves it whole. The demo page route is removed.
- `src/session/identity.py`: asks NETIQ who owns the cookie (path set by `NETIQ_USERINFO_PATH`, default `/auth/me`), and lets the table page and export routes read the session.
- `src/api/routes/reports.py` and `src/api/routes/export.py`: accept the NETIQ login.
- `src/api/middleware.py`: `POST /v1/session/netiq` is written to `audit.log` as a login.
- `configs/api_routes.yaml`: `/v1/session/netiq` added, `/chat-demo` removed.
- Removed: `ui/web/chat_demo.html` (the old demo page) and its route `GET /chat-demo`.
- Tests: `tests/workflow/test_conversation_api.py` and `tests/unit/test_streamlit_ui.py`.

How to try it

1. Start the NETIQ backend on port 6061 (needed for login).
2. From this folder, start the service: `python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000`.
3. Start the UI: `python -m streamlit run ui/streamlit/app.py --server.address 127.0.0.1 --server.port 8501`.
4. Log in to NETIQ at http://127.0.0.1:6061, then open http://127.0.0.1:8501 in the same browser. Use the same host name for both.
5. Ask "How many 4G cells are available in Bihar?", then "and 5G?". The second answer says "Follow-up, so chat history was sent".
6. Click New Conversation, then click the first chat under My chats. It opens again with its table.

Run the tests: `python -m pytest tests/workflow/test_conversation_api.py tests/unit/test_streamlit_ui.py`

## Logging and Monitoring

Every request now leaves a trail in the `logs/` folder. Each line shows which request it belongs to, so one answer can be followed from the question through every LLM call and NETIQ API call. This uses Python's built-in `logging`, so there are no new packages.

What it does

- Request ID: every request gets an ID, and it appears on every log line that request writes, in every file. If the caller sends an `X-Correlation-ID` header, that ID is used. Otherwise a new one is made. A header value with odd characters or more than 64 characters is replaced with a new ID. The ID is sent back in the `X-Correlation-ID` response header and passed on in the same header to NETIQ API calls.
- One line per request in `api.log`: method, route, status, time taken in ms, and the user name once logged in.
- One line per LLM call in `llm.log`: model, role, time taken, tokens in and out, and tokens per second. A failed call is logged with the error and then raised as before.
- One line per NETIQ API call in `tools.log`: report, mode, circle, rows returned, and time taken, or the error.
- Audit trail in `audit.log`: successful and failed logins, logouts, and requests refused with 401 or 403.
- Errors: every warning and error is also copied to `errors.log`. A crash is written with its full stack trace. The user gets a short 500 reply that includes the request ID, so a complaint can be traced.
- Never logged: passwords, tokens, cookies, session IDs and API keys. They are replaced with `[REDACTED]` wherever they appear, even inside a URL or an error message. The question text is not logged either, only its length. Library lines that print full URLs are switched off, because the NETIQ login can send the password in the URL.
- Format: each line in a file is one JSON object with the same core fields: `timestamp`, `level`, `module`, `event`, `request_id`, plus that event's own fields. The console shows a short, readable version.
- Old files: at midnight each file starts fresh. The old one is kept with the date added to its name. Files are deleted after 30 days, or 90 days for `audit.log`.

Log files

| File | What goes in it |
|---|---|
| `api.log` | one line per request |
| `llm.log` | every LLM call |
| `tools.log` | NETIQ API calls and report tools |
| `agents.log` | orchestrator and agents (empty until they are built) |
| `database.log` | chat database failures and clean-ups |
| `audit.log` | logins, logouts, refused requests |
| `errors.log` | a copy of every warning and error |
| `app.log` | everything else, including server start and stop |

A file is created only when its first line is written, so not all of them show up at once.

Example line from `api.log`:

```json
{"timestamp": "2026-11-26T11:57:34.523+05:30", "level": "INFO", "module": "src.api.middleware", "event": "request_done", "request_id": "e2e-health", "method": "GET", "route": "/health", "status": 200, "duration_ms": 1.9, "user": null}
```

Settings (in `.env` or as environment variables)

- `LOG_LEVEL`: `DEBUG`, `INFO` (default), `WARNING` or `ERROR`.
- `LOG_DIR`: where the files go. The default is `logs/` inside this folder. The `logs/` folder is not committed to git.
- Everything else (files, which code writes to which file, how many days to keep) is in `configs/logging.yaml`.

Monitoring

`python -m src.observability.metrics` prints today's numbers from the log files: requests, server errors, refused requests, average and slowest response times, LLM calls and failures, average LLM time and tokens, calls per model, and NETIQ API calls and failures. Add a date for another day: `python -m src.observability.metrics 2026-11-25`. Alerts and health checks on the server are a separate, later task.

Files added or changed

- `configs/logging.yaml` (new): the one place for all logging settings.
- `src/observability/logging.py`: the JSON line format, the hiding of secrets, and the setup.
- `src/observability/correlation.py`: holds the current request's ID and user.
- `src/observability/audit.py`: the audit logger.
- `src/observability/metrics.py`: the monitoring summary.
- `src/api/middleware.py`: gives each request its ID, writes its line in `api.log` and the audit lines, and catches crashes.
- `src/api/app.py`: two lines that turn logging on and add the middleware.
- `src/adapters/llm/provider.py`: the `llm.log` line for each LLM call.
- `src/adapters/netiq_http/client.py`: the `tools.log` line for each NETIQ API call.
- `src/session/chat_store.py`, `src/session/identity.py` and `src/api/routes/conversations.py`: chat database failures and clean-ups, the user name on the request line, and one line per chat question.
- `.gitignore` (new): keeps `logs/` out of git.
- Tests: `tests/unit/test_logging.py`.

How to try it

1. From this folder, start the service: `python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000`.
2. Send a request with your own ID: `curl.exe -H "X-Correlation-ID: my-test-1" http://127.0.0.1:8000/health`.
3. Open `logs/api.log`. The last line has `"request_id": "my-test-1"`.
4. See the day's numbers: `python -m src.observability.metrics`.

Run the tests: `python -m pytest tests/unit/test_logging.py`


## Fixed Q&A Knowledge Base

The chatbot now answers a fixed set of NETIQ questions (product, scope, architecture, ingestion, security, dashboards, audits, service stitching, AI audit, troubleshooting) with approved answers and source citations. These answers come from the NETIQ Solution Document v3.3 and the User Manual v3.5. They do not use the LLM.

What it does

- Fixed answers first: a question that matches a fixed question is answered with the approved answer word for word, with `SUCCESS` status, intent `KNOWLEDGE` and agent `FIXED_QA_AGENT`. The source (document and section) and the entry ID (for example `NETIQ-STI-001`) are returned in `sources`.
- Matching: spelling, case and punctuation do not matter. Chat-style shortcuts ("wat is srvc stitching") and common Hinglish ("service stitching ka matlab kya hai") also match. A question that matches only loosely is not answered from the fixed set.
- Reports are not hijacked: a request that starts with show, list, get, export and so on, a "which sites / cells..." question, or a question naming a circle, vendor or site ID that the fixed answer does not cover, goes to the normal report route. Keyword-style phrasing (no question word) is answered only when it is an exact saved alias.
- Deployment-specific answers (server sizing, SLA, RPO/RTO, support contacts, SSO/MFA, retention) carry a note and a warning to confirm the value with the NETIQ administrator.
- Questions the fixed set does not cover go on to the existing knowledge agent (SOP-RAN-402, glossary), report and comparison routes, unchanged.

Data files (`data/knowledge/`)

| File | Use |
|---|---|
| `netiq_chatbot_knowledge_base.json` | Main file the bot loads: 199 Q&A entries with alternate questions, keywords, audience, type and sources |
| `netiq_fixed_qa_expanded.json` | One row per question wording, same answer. Used only if the main file is missing |
| `netiq_fixed_qa.json` | One row per question (`id`, `category`, `question`, `answer`). Used only if the two above are missing |
| `netiq_chatbot_knowledge_base.md` | The same content in Markdown, for people and for loading into a knowledge-base tool. The bot does not read it |
| `kb_testset.jsonl` | Test questions with expected route, status and answer checks. Not loaded by the bot |

To add or change an answer, edit `netiq_chatbot_knowledge_base.json` (keep `id`, `question`, `answer`; add other wordings under `alternate_questions`) and restart the service. Set `NETIQ_FIXED_QA_PATH` to load a different file.

Files changed

- `app/orchestrator/chat_service.py`: the fixed Q&A matcher and the guardrails, which run as step 0 of `process_chat` before export, comparison and report routing. Severity questions are also sent to the knowledge agent.
- `data/knowledge/`: the five data files above.
