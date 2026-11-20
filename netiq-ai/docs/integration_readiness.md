# NETIQ Agentic AI — Integration Readiness Report

## 1. Executive Summary & Distinction Matrix

This report provides the formal integration readiness status across all 57 NETIQ UI report presentation groups.
It enforces strict distinction between what is implemented in Python, what is supported by source files, what is verified by automated tests, and what requires live Java API evidence.

| Architecture Dimension | Implemented in Python | Supported by Workbook/CSV | Verified by Offline Tests | Live Java Evidence Needed (Stage 2) |
| :--- | :---: | :---: | :---: | :---: |
| **Pydantic Response Schemas** | **YES** | Partial | **YES** | Real JSON structure match |
| **API Allowlist & Security Gates** | **YES** | **YES** | **YES** | Production endpoint deployment |
| **Metadata-Driven Response Adapters** | **YES** | **YES** | **YES** | Verified dotted JSON paths |
| **MOCK Fixture Execution** | **YES** | **YES** | **YES** | N/A (Offline only) |
| **LIVE HTTP Integration Mode** | **YES** (Gated) | Candidate paths | **YES** (Guards verified) | Authentication & Network verification |
| **Bounded Multi-Page Retrieval** | **YES** | Partial | **YES** | Real total count & pagination semantics |
| **Circle Boundary Authorization** | **YES** | Partial | **YES** | Server-side circle validation |
| **Chat Response & Evidence Composition** | **YES** | **YES** | **YES** | Live data verification |

---

## 2. Key Reconciliation Findings & Anomalies

- **Shared Report Codes**: 2 codes shared across multiple UI groups:
  - `planned-vs-configured-audit`: MW - Planned vs Configured, MW - Configuration Validation, MW - Planned vs Configured (All Validation), MW - MIDS Validation
  - `node-report`: RAN - Node Inventory, RAN - Ghost Node, RAN - eNodeB, RAN - gNodeB, RAN - BTS, RAN - SRAN
- **Missing Read API Mappings**: 3 UI reports have no established read endpoint in supplied controllers:
  - Report #51 (AI - Site Inference): AI site/node/cell inference UI group lacks confirmed distinct read API mapping.
  - Report #52 (AI - Node Inference): AI site/node/cell inference UI group lacks confirmed distinct read API mapping.
  - Report #53 (AI - Cell Inference): AI site/node/cell inference UI group lacks confirmed distinct read API mapping.
- **Conflicting Endpoints**: 1 report codes exhibit divergent endpoint/DTO mappings:
  - `ip-data-audit-report`: Code exists in both Inventory (POST /api/nodes/reports/ip-data-audit-report via ReportRequest) and Audit (POST /api/v1/audit/reports/ip-data-audit-report via AuditReportRequest).
- **Unmapped Inventory Enum Codes**: 25 codes in `ReportRequestType.java` not represented in UI groups.
- **Unmapped Audit Enum Codes**: 27 codes in `AuditReportType.java` not represented in UI groups.

---

## 3. Comprehensive Report-by-Report Status Table (57 UI Reports)

| # | Report ID | Domain | API Candidate | API Mapping | Field Mapping | Response Contract | Pagination | Auth Readiness | MOCK Status | LIVE Eligibility |
| :-: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `AI_MISSING_PARAMETER_PREDICTIONS` | AI | `POST /api/nodes/reports/prediction-all-missing` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 2 | `AI_BASELINE_AUDIT` | AI | `POST /api/nodes/reports/ai-baseline-all` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 3 | `AI_DISMANTLED_HARDWARE_INTELLIGENCE` | AI | `POST /api/nodes/reports/ai-dismantled-hardware` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 4 | `AI_MW_FREQUENCY_DEVIATION` | AI | `POST /api/nodes/reports/ai-mw-deviation-all` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 5 | `MW_UBR_NODE_INVENTORY` | MW / UBR | `POST /api/nodes/reports/mw-node` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 6 | `MW_UBR_DUPLICATE_NODES_MWDUPLICATENODES` | MW / UBR | `POST /api/nodes/reports/mw-duplicate-node` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 7 | `MW_UBR_PORT_INVENTORY` | MW / UBR | `POST /api/nodes/reports/mw-port` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 8 | `MW_UBR_VLAN_INVENTORY` | MW / UBR | `POST /api/nodes/reports/mw-vlan` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 9 | `WIRELINE_NODE_INVENTORY` | Wireline | `POST /api/nodes/reports/wireline-node` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 10 | `MW_UBR_SITE_INVENTORY` | MW / UBR | `POST /api/nodes/reports/mw-site` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 11 | `MW_UBR_IP_INVENTORY` | MW / UBR | `POST /api/nodes/reports/mw-ip` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 12 | `MW_UBR_NODE_VALIDATION` | MW / UBR | `POST /api/v1/audit/reports/mw-node-audit` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 13 | `MW_TRANSMISSION_LINK_INVENTORY` | MW | `POST /api/nodes/reports/mw-tr-link` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 14 | `MW_CAPACITY_HOP` | MW | `POST /api/nodes/reports/mw-hop-config-report` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 15 | `UBR_TRANSMISSION_LINK_INVENTORY` | UBR | `POST /api/nodes/reports/ubr-tr-link` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 16 | `UBR_TRANSMISSION_LINK_AUDIT` | UBR | `POST /api/v1/audit/reports/TXN/ubr-tr-audit` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 17 | `MW_PLANNED_VS_CONFIGURED` | MW | `POST /api/v1/audit/reports/TXN/planned-vs-configured-audit` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 18 | `MW_DUPLICATE_NODE_AUDIT` | MW | `POST /api/v1/audit/reports/duplicate_mw_node` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 19 | `MW_LINK_AUDIT` | MW | `POST /api/v1/audit/reports/TXN/mw-tr-link-audit` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 20 | `RAN_NODE_INVENTORY` | RAN | `POST /api/nodes/reports/node-report` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 21 | `RAN_GHOST_NODE` | RAN | `POST /api/nodes/reports/node-report` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 22 | `RAN_ENODEB` | RAN | `POST /api/nodes/reports/node-report` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 23 | `RAN_GNODEB` | RAN | `POST /api/nodes/reports/node-report` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 24 | `RAN_BTS` | RAN | `POST /api/nodes/reports/node-report` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 25 | `RAN_SRAN` | RAN | `POST /api/nodes/reports/node-report` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 26 | `MW_HARDWARE_VALIDATION` | MW | `POST /api/nodes/reports/mw-hard-cab` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 27 | `RAN_CELL_4G` | RAN | `POST /api/nodes/reports/4g` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 28 | `RAN_CELL_5G` | RAN | `POST /api/nodes/reports/5g` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 29 | `RAN_CELL_2G` | RAN | `POST /api/nodes/reports/2g` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 30 | `RAN_IP_INVENTORY` | RAN | `POST /api/nodes/reports/ip-data` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 31 | `MW_CONFIGURATION_VALIDATION` | MW | `POST /api/v1/audit/reports/TXN/planned-vs-configured-audit` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 32 | `RAN_CORE_IP` | RAN | `POST /api/nodes/reports/core-ip-data` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 33 | `RAN_BOARD_HARDWARE` | RAN | `POST /api/nodes/reports/boards` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 34 | `RAN_CABINET_HARDWARE` | RAN | `POST /api/nodes/reports/cabinet` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 35 | `MW_UBR_BOARD_HARDWARE` | MW / UBR | `POST /api/nodes/reports/mw-board` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 36 | `MW_UBR_TRANSCEIVER` | MW / UBR | `POST /api/nodes/reports/mw-transceiver` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 37 | `MW_TRANSMISSION_LINK_TXN_VARIANT` | MW | `POST /api/nodes/reports/mw-trlink-combined` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 38 | `MW_PLANNED_VS_CONFIGURED_ALL_VALIDATION` | MW | `POST /api/v1/audit/reports/TXN/planned-vs-configured-audit` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 39 | `WIRELINE_HARDWARE` | Wireline | `POST /api/nodes/reports/wireline-hardware` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 40 | `WIRELINE_LOGICAL_INTERFACE` | Wireline | `POST /api/nodes/reports/wireline-logical` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 41 | `WIRELINE_VLAN_IP` | Wireline | `POST /api/nodes/reports/wireline-vlan` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 42 | `FTTH_NODE_INVENTORY` | FTTH | `POST /api/nodes/reports/ftth-node` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 43 | `FTTH_PORT_INVENTORY` | FTTH | `POST /api/nodes/reports/ftth-port` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 44 | `FTTH_HARDWARE` | FTTH | `POST /api/nodes/reports/ftth-hardware` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 45 | `FTTH_LINK_INVENTORY` | FTTH | `POST /api/nodes/reports/ftth-link` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 46 | `MW_MIDS_VALIDATION` | MW | `POST /api/v1/audit/reports/TXN/planned-vs-configured-audit` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 47 | `WIRELINE_PORT_INVENTORY` | Wireline | `POST /api/nodes/reports/wireline-port` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 48 | `WIRELINE_LINK_INVENTORY` | Wireline | `POST /api/nodes/reports/wireline-link` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 49 | `STITCHING_END_TO_END_SERVICE_REPORT` | Stitching | `POST /api/v1/stitching/report` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 50 | `NETWORK_CHANGE_DETAILS` | Network | `POST /api/nodes/reports/change-details` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 51 | `AI_SITE_INFERENCE` | AI | `NONE` | NOT_AVAILABLE | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | NO_API | **BLOCKED** |
| 52 | `AI_NODE_INFERENCE` | AI | `NONE` | NOT_AVAILABLE | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | NO_API | **BLOCKED** |
| 53 | `AI_CELL_INFERENCE` | AI | `NONE` | NOT_AVAILABLE | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | NO_API | **BLOCKED** |
| 54 | `AI_CELL_TO_RU_LINK_AUDIT` | AI | `POST /api/nodes/reports/cell-to-ru` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 55 | `AI_RAN_UPGRADE_AND_LOCATION_INTELLIGENCE` | AI | `POST /api/nodes/reports/ran-upgrade` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 56 | `AI_RAN_GPS_IMPUTATION` | AI | `POST /api/nodes/reports/ran-gps-imputation` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |
| 57 | `AI_DAILY_NETWORK_CHANGE_SUMMARY` | AI | `GET /api/v1/ai/daily-change/summary` | SOURCE_DERIVED | SOURCE_DERIVED | UNVERIFIED | UNVERIFIED | UNVERIFIED | READY | **BLOCKED** |

---

## 4. Definition of Done Checklist

### Stage 1 (Complete)
- [x] Valid report metadata loaded into version-controlled catalog.
- [x] Source-derived API mappings represented without overclaiming verification.
- [x] Standard Pydantic v2 response schemas implemented.
- [x] Synthetic fixtures normalize cleanly through response adapters.
- [x] Invalid responses, malformed payloads, and contradictory paginations produce explicit errors.
- [x] Strict endpoint allowlist enforces exact path-template matching with no wildcards.
- [x] Hazardous mutation routes (SQL consoles, bulk ETL imports) positively excluded.
- [x] MOCK mode produces clearly labeled results with provenance disclaimers.
- [x] All 44 offline automated tests pass without network or backend dependencies.
- [x] System strictly prevents accidental execution of unverified production APIs.

### Stage 2 (Awaiting Java Team Backend Evidence)
- [ ] Real JSON response payloads captured from live Java Spring Boot runtime.
- [ ] Dotted response paths (`data`, `pagination.totalRecords`, `hasNext`) confirmed against real contracts.
- [ ] UI column IDs reconciled with actual Oracle DB column names and SQL types.
- [ ] Server-side authentication (Bearer token / OAuth) and circle security audited.
- [ ] Total count calculations and filter operators approved by telecom domain owners.
- [ ] Production LIVE mode enabled upon passing live contract verification tests.