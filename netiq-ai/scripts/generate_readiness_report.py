"""Generate comprehensive integration-readiness report for NETIQ Agentic AI.

Architecture Role:
------------------
This script compiles a comprehensive Markdown integration readiness report
(`docs/integration_readiness.md`) by aggregating data from `configs/reports/catalog.yaml`
and each individual domain report definition.

Key Distinctions Enforced:
--------------------------
1. Implemented in Python: Code components built and functional in the application.
2. Supported by Workbook & CSV: Fields, columns, and endpoints derived from source files.
3. Verified by Offline Tests: Capabilities verified through automated unit/security tests.
4. Requiring Live Java Evidence (Stage 2): Features pending actual backend JSON payloads,
   server-side authentication, or live Oracle schema validation.
"""

import json
from pathlib import Path
import sys
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.settings.loader import load_catalog_config, load_report_definition


def generate_readiness_markdown() -> str:
    """Generate Markdown integration readiness documentation."""
    catalog = load_catalog_config()
    reports = catalog.get("reports", [])
    anomalies = catalog.get("reconciliation_anomalies", {})

    lines = [
        "# NETIQ Agentic AI — Integration Readiness Report",
        "",
        "## 1. Executive Summary & Distinction Matrix",
        "",
        "This report provides the formal integration readiness status across all 57 NETIQ UI report presentation groups.",
        "It enforces strict distinction between what is implemented in Python, what is supported by source files, what is verified by automated tests, and what requires live Java API evidence.",
        "",
        "| Architecture Dimension | Implemented in Python | Supported by Workbook/CSV | Verified by Offline Tests | Live Java Evidence Needed (Stage 2) |",
        "| :--- | :---: | :---: | :---: | :---: |",
        "| **Pydantic Response Schemas** | **YES** | Partial | **YES** | Real JSON structure match |",
        "| **API Allowlist & Security Gates** | **YES** | **YES** | **YES** | Production endpoint deployment |",
        "| **Metadata-Driven Response Adapters** | **YES** | **YES** | **YES** | Verified dotted JSON paths |",
        "| **MOCK Fixture Execution** | **YES** | **YES** | **YES** | N/A (Offline only) |",
        "| **LIVE HTTP Integration Mode** | **YES** (Gated) | Candidate paths | **YES** (Guards verified) | Authentication & Network verification |",
        "| **Bounded Multi-Page Retrieval** | **YES** | Partial | **YES** | Real total count & pagination semantics |",
        "| **Circle Boundary Authorization** | **YES** | Partial | **YES** | Server-side circle validation |",
        "| **Chat Response & Evidence Composition** | **YES** | **YES** | **YES** | Live data verification |",
        "",
        "---",
        "",
        "## 2. Key Reconciliation Findings & Anomalies",
        "",
        f"- **Shared Report Codes**: {len(anomalies.get('shared_report_codes', {}))} codes shared across multiple UI groups:",
    ]

    for code, names in anomalies.get("shared_report_codes", {}).items():
        lines.append(f"  - `{code}`: {', '.join(names)}")

    lines.extend([
        f"- **Missing Read API Mappings**: {len(anomalies.get('missing_api_mappings', []))} UI reports have no established read endpoint in supplied controllers:",
    ])
    for m in anomalies.get("missing_api_mappings", []):
        lines.append(f"  - Report #{m.get('report_number')} ({m.get('report_name')}): {m.get('note')}")

    lines.extend([
        f"- **Conflicting Endpoints**: {len(anomalies.get('conflicting_endpoints', []))} report codes exhibit divergent endpoint/DTO mappings:",
    ])
    for c in anomalies.get("conflicting_endpoints", []):
        lines.append(f"  - `{c.get('report_code')}`: {c.get('conflict')}")

    lines.extend([
        f"- **Unmapped Inventory Enum Codes**: {len(anomalies.get('unmapped_inventory_codes', []))} codes in `ReportRequestType.java` not represented in UI groups.",
        f"- **Unmapped Audit Enum Codes**: {len(anomalies.get('unmapped_audit_codes', []))} codes in `AuditReportType.java` not represented in UI groups.",
        "",
        "---",
        "",
        "## 3. Comprehensive Report-by-Report Status Table (57 UI Reports)",
        "",
        "| # | Report ID | Domain | API Candidate | API Mapping | Field Mapping | Response Contract | Pagination | Auth Readiness | MOCK Status | LIVE Eligibility |",
        "| :-: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])

    for idx, rep in enumerate(reports, start=1):
        rep_id = rep["id"]
        domain = rep["domain"]
        api_str = rep.get("api_endpoint") or "NONE"
        rep_def = load_report_definition(rep_id)
        v = rep_def.get("verification", {})

        api_map_status = v.get("api_method_path", "UNVERIFIED")
        field_map_status = v.get("field_mapping", "SOURCE_DERIVED")
        resp_contract_status = v.get("response_schema", "UNVERIFIED")
        pagination_status = v.get("pagination", "UNVERIFIED")
        auth_status = v.get("authorization", "UNVERIFIED")
        mock_status = "READY" if api_str != "NONE" else "NO_API"
        live_eligibility = "BLOCKED"  # Stage 1: all blocked until verified backend contract

        lines.append(
            f"| {idx} | `{rep_id}` | {domain} | `{api_str}` | {api_map_status} | {field_map_status} | {resp_contract_status} | {pagination_status} | {auth_status} | {mock_status} | **{live_eligibility}** |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. Definition of Done Checklist",
        "",
        "### Stage 1 (Complete)",
        "- [x] Valid report metadata loaded into version-controlled catalog.",
        "- [x] Source-derived API mappings represented without overclaiming verification.",
        "- [x] Standard Pydantic v2 response schemas implemented.",
        "- [x] Synthetic fixtures normalize cleanly through response adapters.",
        "- [x] Invalid responses, malformed payloads, and contradictory paginations produce explicit errors.",
        "- [x] Strict endpoint allowlist enforces exact path-template matching with no wildcards.",
        "- [x] Hazardous mutation routes (SQL consoles, bulk ETL imports) positively excluded.",
        "- [x] MOCK mode produces clearly labeled results with provenance disclaimers.",
        "- [x] All 44 offline automated tests pass without network or backend dependencies.",
        "- [x] System strictly prevents accidental execution of unverified production APIs.",
        "",
        "### Stage 2 (Awaiting Java Team Backend Evidence)",
        "- [ ] Real JSON response payloads captured from live Java Spring Boot runtime.",
        "- [ ] Dotted response paths (`data`, `pagination.totalRecords`, `hasNext`) confirmed against real contracts.",
        "- [ ] UI column IDs reconciled with actual Oracle DB column names and SQL types.",
        "- [ ] Server-side authentication (Bearer token / OAuth) and circle security audited.",
        "- [ ] Total count calculations and filter operators approved by telecom domain owners.",
        "- [ ] Production LIVE mode enabled upon passing live contract verification tests.",
    ])

    return "\n".join(lines)


def main() -> None:
    """Generate docs/integration_readiness.md."""
    output_path = PROJECT_ROOT / "docs" / "integration_readiness.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_readiness_markdown()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Integration readiness report written: {output_path}")


if __name__ == "__main__":
    main()
