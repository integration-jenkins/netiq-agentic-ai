# Architecture overview (sample)

Request path: Java gateway -> FastAPI (`src/api`) -> Orchestrator (`app/orchestrator`) ->
Data Extraction Tools / Knowledge Agent / SQL Agent (fallback) -> adapters (`src/adapters`).

- Only `src/adapters/` performs external I/O.
- `src/tools/data_extraction/` never calls an LLM.
- Allowed NETIQ APIs are defined in `configs/allowed_apis.yaml`.
