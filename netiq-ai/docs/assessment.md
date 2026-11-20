# Assessment Report: NETIQ Agentic AI Project Baseline

## 1. Executive Summary

An exhaustive analysis of the codebase at `netiq-ai/` and the supplied project input files (`NETIQ_AI_Report_Catalogue_and_API_Mapping.xlsx` and `NETIQ_Java_API_Inventory.csv`) was conducted. The project structure matches the intended enterprise repository layout, but all functional modules across `src/`, `app/orchestrator/`, and `configs/` were found to be empty single-line placeholder docstrings or skeleton files.

This assessment outlines the gap between the placeholder scaffold and a production-grade Response Standardization Layer, establishing the foundation for Stage 1 implementation.

---

## 2. Codebase Component Assessment

| Subsystem / Module | File Path | Existing State | Gap / Missing Elements |
| :--- | :--- | :--- | :--- |
| **Response Schemas** | `src/schemas/reports.py`<br>`src/schemas/chat.py`<br>`src/schemas/evidence.py`<br>`src/schemas/errors.py`<br>`src/schemas/metadata.py` | Placeholder docstrings only (`"""..."""`). | Missing `ReportQuery`, `ReportPagination`, `ReportSource`, `ReportPage`, `ChatResponse`, `StandardError`, and metadata definition Pydantic models. |
| **HTTP Client & Adapters** | `src/adapters/netiq_http/client.py`<br>`src/adapters/netiq_http/allowed_api.py`<br>`src/adapters/netiq_http/response_adapters.py` | Placeholder docstrings only. | Missing `httpx.AsyncClient` connection pooling, MOCK/LIVE mode gating, allowlist policy matching, safe dotted-path extraction, pagination parsing, and field aliasing. |
| **Configuration Loading** | `src/settings/env.py`<br>`src/settings/loader.py`<br>`configs/allowed_apis.yaml`<br>`configs/limits.yaml` | `allowed_apis.yaml` is `[]`, `limits.yaml` is `{}`, Python loaders are docstrings. | Missing YAML fail-closed loading, environment variable schema validation, runtime query/pagination limits enforcement. |
| **Security & Authorization**| `src/security/authentication.py`<br>`src/security/authorization.py`<br>`src/security/circle_access.py` | Placeholder docstrings only. | Missing circle-level isolation (e.g. verifying user circle matches report circle), Bearer token extraction, and unverified contract execution guards. |
| **Data Retrieval Tools** | `src/tools/data_extraction/retrieval.py` | Placeholder docstring only. | Missing single-page and bounded multi-page fetching, pagination sanity validation, infinite loop protection, and aggregate count optimizations. |
| **Orchestrator Verification & Composition** | `app/orchestrator/verify.py`<br>`app/orchestrator/compose.py` | Placeholder docstrings only. | Missing deterministic calculation verification, evidence linking, and ChatResponse formatting with explicit MOCK/LIVE disclaimers. |
| **Report Metadata Scripts** | `scripts/generate_report_metadata.py`<br>`scripts/validate_metadata.py` | Placeholder docstrings only. | Missing Excel workbook parsing (5 sheets), reconciliation logic, cross-checking against Java API CSV, and YAML catalog generation. |
| **Automated Tests** | `tests/unit/`<br>`tests/security/`<br>`tests/workflow/`<br>`tests/failure/` | 6 trivial placeholder tests passing (checking sample YAML exists and dataset not empty); 1 skipped e2e test. | Missing comprehensive tests for Pydantic validation, adapter extraction, allowlist enforcement, circle access, failure modes, and mock retrieval. |

---

## 3. Input Files & Metadata Reconciliation Findings

1. **Excel Structure**:
   - `57 UI Reports`: 57 presentation groups across 9 domains (`RAN`, `MW`, `MW / UBR`, `UBR`, `Wireline`, `FTTH`, `AI`, `Stitching`, `Network`).
   - `64 Inventory Codes`: Enums in `ReportRequestType.java` utilizing `POST /api/nodes/reports/{reportType}` with `ReportRequest` DTO.
   - `32 Audit Codes`: Enums in `AuditReportType.java` utilizing `POST /api/v1/audit/reports/{type}` and `POST /api/v1/audit/reports/TXN/{type}` with `AuditReportRequest` or `DataRequest` DTO.
   - `1233 Column Mappings`: 1,233 rows mapping UI column IDs, UI headers, and DTO accessors across the 57 reports with zero row count discrepancies.
   - `Read Me`: Clarifies that groups overlap (not 153 separate reports) and emphasizes that POST endpoints are read-only report retrieval.

2. **Reconciliation Anomalies**:
   - **Shared Report Codes**: Report code `node-report` is shared by 6 UI reports (#20-#25). Report code `planned-vs-configured-audit` is shared by 4 UI reports (#17, #31, #38, #46).
   - **Missing Read APIs**: Reports #51, #52, #53 ("AI - Site/Node/Cell Inference") lack confirmed read endpoints in the supplied Java controllers.
   - **Conflicting Endpoints & DTOs**: `ip-data-audit-report` exists in both Inventory codes (`/api/nodes/reports/ip-data-audit-report` via `ReportRequest`) and Audit codes (`/api/v1/audit/reports/ip-data-audit-report` via `AuditReportRequest`), plus legacy GET routes in `AuditController.java`.
   - **UI vs DTO Key Differences**: 147 columns exhibit case or naming divergence between `UI Column ID` and `DTO Accessor` (e.g. `Cabinet` vs `cabinet`, `Circle` vs `circle`).

3. **CSV Allowlist Analysis (201 endpoints)**:
   - Positively approved read-only candidates: Report retrieval endpoints (`/api/nodes/reports/{reportType}`, `/api/v1/audit/reports/{type}`, `/api/v1/stitching/report`, etc.).
   - Explicitly excluded mutation/hazardous routes: `DbConsoleController` (arbitrary SQL execution), `UnifiedImportController` / `DataParsingController` (file upload/ETL import/refresh), `FrequencyController` (frequency sync), `CellToRuMappingController` (model training), and all `*/export` endpoints.

---

## 4. Stage 1 Execution Strategy

1. Implement fail-closed settings loader (`src/settings/`) and configuration limits (`configs/limits.yaml`).
2. Build `scripts/generate_report_metadata.py` to generate the complete catalog and domain YAMLs with provenance and verification statuses.
3. Build `scripts/validate_metadata.py` to ensure schema conformance and allowlist consistency.
4. Construct `configs/allowed_apis.yaml` and enforce exact path-template matching in `src/adapters/netiq_http/allowed_api.py`.
5. Implement Pydantic v2 data models in `src/schemas/reports.py`, `src/schemas/metadata.py`, `src/schemas/evidence.py`, `src/schemas/errors.py`, and `src/schemas/chat.py`.
6. Implement the response adapter engine in `src/adapters/netiq_http/response_adapters.py` with safe dotted-path navigation.
7. Generate representative synthetic fixtures in `data/fixtures/` covering positive, empty, malformed, and error cases.
8. Implement `NetIQHttpClient` supporting MOCK mode with synthetic fixtures and gating LIVE mode behind verified contracts.
9. Implement `ReportRetrievalService` in `src/tools/data_extraction/retrieval.py` with multi-page bounds and loop safety.
10. Implement response verification and composition in `app/orchestrator/verify.py` and `app/orchestrator/compose.py`.
11. Build a comprehensive suite of offline unit, security, workflow, and failure tests.
