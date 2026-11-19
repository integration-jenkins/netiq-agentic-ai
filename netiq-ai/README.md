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
