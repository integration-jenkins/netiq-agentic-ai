# NETIQ Agentic AI — Streamlit UI & Backend API Integration

**Document Status:** Implemented & Verified  
**Target Environment:** Offline Local Deployment (FastAPI + Streamlit + Ollama)  
**Last Updated:** November 2026  

---

## 1. Architecture Overview

The Streamlit UI is strictly **API-driven** and communicates exclusively with the FastAPI backend via HTTPX REST calls. Streamlit never imports orchestrators, LLM clients, Ollama adapters, or Oracle database modules directly, allowing the exact same FastAPI contracts to be reused by the NETIQ React frontend.

```text
Streamlit UI (ui/streamlit/)
     │
     │ HTTPX REST APIs (NETIQ_AI_BASE_URL)
     ▼
FastAPI Backend (src/api/)
     ├── GET  /health?details=true
     ├── POST /v1/chat
     ├── GET  /v1/metadata/{circles,domains,reports,agents}
     ├── GET  /v1/results/{result_id}
     ├── POST /v1/export  &  GET /v1/export/{file_id}
     ├── POST /v1/inference
     └── POST /v1/agents/test
     ▼
Orchestration & Agents (app/orchestrator/, app/llms/, src/tools/)
     ├── ChatService (follow-ups, comparison, knowledge, reports)
     ├── ReportSelector (canonical catalog matching)
     ├── KnowledgeAgent (grounded SOPs + threshold rules)
     ├── ReportRetrievalService (MOCK fixtures / LIVE Java APIs)
     ├── ResultStore (verified snapshots + pagination + ownership)
     └── ExcelExportService (OpenPyXL write-only + formula injection guard)
```

---

## 2. Updated Project Structure

```text
netiq-ai/
├── .streamlit/
│   └── config.toml                          # Disables telemetry; binds 127.0.0.1:8501
├── requirements.txt                         # Includes streamlit, pandas, openpyxl, sqlglot, httpx, fastapi
├── configs/
│   └── api_routes.yaml                      # Registers all implemented FastAPI routes
├── app/orchestrator/
│   └── chat_service.py                      # End-to-end ChatService orchestration
├── src/
│   ├── api/
│   │   ├── app.py                           # Exposes `app = create_app()` for uvicorn
│   │   └── routes/
│   │       ├── agents.py                    # POST /v1/agents/test (dev/admin restricted)
│   │       ├── chat.py                      # POST /v1/chat
│   │       ├── export.py                    # POST /v1/export & GET /v1/export/{file_id}
│   │       ├── health.py                    # GET /health & GET /health?details=true
│   │       ├── metadata.py                  # Circles, domains, reports, agents metadata
│   │       └── reports.py                   # GET /v1/results/{result_id} & POST /v1/reports/query
│   ├── schemas/
│   │   ├── chat.py                          # Extended ChatRequest / ChatResponse + TablePayload / MetricCard / SourceReference
│   │   └── export.py                        # ExportRequest / ExportResponse
│   ├── session/
│   │   └── result_store.py                  # Thread-safe verified result & session store
│   └── tools/export/
│       └── excel.py                         # OpenPyXL streaming XLSX generator + formula sanitization
├── ui/streamlit/
│   ├── app.py                               # Main chat UI entrypoint
│   ├── config.py                            # Env-backed UIConfig
│   ├── api_client.py                        # Centralized HTTPX client
│   ├── session_manager.py                   # st.session_state management
│   ├── components/
│   │   ├── sidebar.py                       # Dynamic circles, domains, reports, auth, health indicator
│   │   ├── chat_panel.py                    # Chat history, example prompts, follow-ups
│   │   ├── metric_cards.py                  # Dynamic KPI cards
│   │   ├── data_table.py                    # Dynamic st.dataframe() + server-side pagination & search
│   │   ├── charts.py                        # Safe bar charts for verified numeric aggregations
│   │   ├── source_panel.py                  # Data date, version, circle, mode expander
│   │   ├── export_panel.py                  # Prepare & download XLSX via st.download_button
│   │   └── error_panel.py                   # Safe error display & retry
│   └── pages/
│       ├── 1_Agent_Testing.py               # Developer agent testing console
│       └── 2_System_Health.py               # System health & readiness dashboard
└── tests/
    ├── unit/test_api_smoke.py
    ├── unit/test_streamlit_ui.py            # Streamlit AppTest UI suite
    └── workflow/test_chat_and_export_api.py # Full API, pagination, export & auth integration tests
```

---

## 3. Implemented API Endpoints

| Method | Endpoint | Purpose | Auth / Policy |
|---|---|---|---|
| `GET` | `/health` | Liveness & optional `?details=true` subsystem diagnostics | Public liveness; admin fields gated |
| `POST` | `/v1/chat` | Orchestrate question, return standardized `ChatResponse` | Circle authorization enforced |
| `GET` | `/v1/metadata/circles` | Authorized circles for caller | Token / user circle list |
| `GET` | `/v1/metadata/domains` | Supported domains from `catalog.yaml` | Authenticated |
| `GET` | `/v1/metadata/reports` | Permitted reports (optional `?domain=`) | Authenticated |
| `GET` | `/v1/metadata/reports/{report_id}` | Single report YAML definition | Authenticated |
| `GET` | `/v1/metadata/agents` | Available testable agents & configured models | Authenticated |
| `POST` | `/v1/reports/query` | Direct `ReportQuery` -> `ReportPage` | Circle authorization enforced |
| `GET` | `/v1/results/{result_id}` | Paginated slice + search of verified cached result | Owner + circle verified |
| `POST` | `/v1/export` | Generate `.xlsx` workbook from verified `resultId` | Owner + circle verified |
| `GET` | `/v1/export/{file_id}` | Download generated `.xlsx` file | Owner + safe path verified |
| `POST` | `/v1/inference` | Direct LLM role inference | Model allowlist + prompt gate |
| `POST` | `/v1/agents/test` | Individual agent diagnostic execution | **Developer / Admin only (`403` otherwise)** |

---

## 4. Excel Export Implementation (`src/tools/export/excel.py`)

- **Memory-Efficient Streaming:** Uses `openpyxl.Workbook(write_only=True)` so large datasets stream row-by-row.
- **Full Verified Result:** Exports all rows in the verified `VerifiedResult` snapshot (not just the currently viewed UI page), preserving original filters, `dataVersion`, and `dataAsOf`.
- **Metadata Provenance Sheet:** Every workbook includes a `Metadata` sheet recording Report Name, Report ID, Domain, Circle, Mode (`MOCK`/`LIVE`), Data Version, Data Date, Applied Filters, Total Records, and Export Timestamp.
- **Spreadsheet Formula Injection Protection:** `sanitize_excel_cell()` prepends `'` to any string beginning with `=`, `+`, `-`, `@`, `\t`, or `\r`.
- **Sheet Splitting:** Automatically splits rows across `Data`, `Data_2`, etc. when exceeding `max_rows_per_sheet` (default `1,000,000`).
- **Path Traversal & Cleanup:** Validates `file_id` against `^[A-Za-z0-9_-]{4,64}$`, resolves paths strictly inside `data/exports/`, verifies `owner_username`, and purges expired files after TTL.

---

## 5. Security Controls Verified

- **Backend-Only Authorization:** All circle, result ownership, export ownership, and developer-testing checks execute inside FastAPI.
- **Safe UI Rendering:** Streamlit renders model responses using standard `st.markdown()` without `unsafe_allow_html=True`.
- **No Direct External Calls from UI:** Streamlit never connects to Ollama, Oracle, or Java APIs directly.
- **Developer Gate:** `POST /v1/agents/test` rejects non-admin/non-developer callers with HTTP `403`.
- **SQL Safety:** `sql_agent` testing validates generated SQL with `OracleSQLGuard` (`sqlglot`) and keeps `LIVE_SQL_EXECUTION_ENABLED = False`.

---

## 6. Automated Test Results

Executed from the repository root (`d:\PROJECTS\NETQ GIT\netiq-agentic-ai`):

```powershell
$env:PYTHONPATH="netiq-ai;netiq-ai\src"
pytest netiq-ai/tests -v --tb=short
```

- **Total Tests Collected:** 126
- **Passed:** **125 passed**
- **Skipped:** 1 skipped (`tests/e2e/test_sample_e2e.py::test_health_endpoint`, requires live standalone server)
- **Failed:** **0 failed**
- **Total Duration:** 23.98s

UI tests (`tests/unit/test_streamlit_ui.py`) verified with `streamlit.testing.v1.AppTest` using mocked HTTPX transport:
- Header, `MOCK Data Mode Active` banner, and dynamic sidebar metadata rendering.
- Chat submission rendering natural-language answer, KPI metric cards, dynamic `st.dataframe()`, source panel, and export availability.
- Zero duplicate `/v1/chat` or `/v1/metadata/*` API calls across Streamlit reruns.
- Session reset (`New Conversation`) and backend-disconnected error handling.

---

## 7. Local & Offline Startup Instructions

### Offline Wheelhouse Installation
On a connected staging machine:
```powershell
pip download -r netiq-ai/requirements.txt -d ./wheelhouse
```
On the offline target machine:
```powershell
pip install --no-index --find-links=./wheelhouse -r netiq-ai/requirements.txt
```

### Starting Services (from `netiq-ai/` directory)

1. **Start FastAPI Backend:**
   ```powershell
   python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
   ```
2. **Start Streamlit UI:**
   ```powershell
   streamlit run ui/streamlit/app.py --server.address 127.0.0.1 --server.port 8501
   ```

| Service | Local URL |
|---|---|
| **Streamlit UI** | `http://127.0.0.1:8501` |
| **FastAPI Backend** | `http://127.0.0.1:8000` |
| **Swagger API Docs** | `http://127.0.0.1:8000/docs` |
| **Ollama Daemon** | `http://127.0.0.1:11434` |

### UI Environment Variables
```env
NETIQ_AI_BASE_URL=http://127.0.0.1:8000
NETIQ_AI_API_KEY=
NETIQ_AI_REQUEST_TIMEOUT=120
NETIQ_AI_METADATA_TIMEOUT=15
```

---

## 8. Remaining Limitations & Production Dependencies

1. **In-Memory `ResultStore`:** `src/session/result_store.py` currently stores verified results and session state in-memory with a 1-hour TTL. For multi-worker horizontal scaling in production, back `ResultStore` with Redis or shared storage.
2. **LIVE Java API Contracts:** Report definitions in `configs/reports/` remain `SOURCE_DERIVED` until live NETIQ Java Spring Boot JSON payloads are verified and promoted in `configs/allowed_apis.yaml`.
3. **Authentication Enforcement:** Set `ENFORCE_API_AUTH=true` and configure `NETIQ_APP_AUTH_TOKEN` / SSO identity integration before exposing endpoints outside localhost.
