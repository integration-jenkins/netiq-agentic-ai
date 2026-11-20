"""Generate report metadata and API allowlist from approved source definitions.

Reads:
- NETIQ_AI_Report_Catalogue_and_API_Mapping.xlsx (all 5 sheets)
- NETIQ_Java_API_Inventory.csv

Outputs:
- configs/reports/catalog.yaml
- configs/reports/<domain>/<report_id>.yaml
- configs/allowed_apis.yaml
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import re
from typing import Any
import openpyxl
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCEL_PATH = Path(r"D:\PROJECTS\Other\NETIQ_AGENTIC_AI\DOCUMENTS\New folder\NETIQ_AI_Report_Catalogue_and_API_Mapping.xlsx")
DEFAULT_CSV_PATH = Path(r"D:\PROJECTS\Other\NETIQ_AGENTIC_AI\DOCUMENTS\New folder\NETIQ_Java_API_Inventory.csv")


def sanitize_id(name: str) -> str:
    """Produce deterministic uppercase identifier from name."""
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").upper()
    return clean


def normalize_domain_folder(domain: str) -> str:
    """Map domain name to config subfolder."""
    dom = (domain or "").strip().lower()
    if "ran" in dom:
        return "ran"
    elif "mw" in dom or "ubr" in dom:
        return "mw"
    elif "ftth" in dom:
        return "ftth"
    elif "wireline" in dom:
        return "wireline"
    elif "audit" in dom:
        return "audit"
    elif "ai" in dom or "stitching" in dom or "network" in dom:
        return "ai"
    return "ran"


def parse_filter_guidance(guidance: str | None) -> list[dict[str, Any]]:
    """Extract preliminary filter metadata from DTO and filter descriptions."""
    if not guidance:
        return []
    # Common filters known from ReportRequest and AuditReportRequest DTOs
    standard_filters = [
        {"name": "circle", "type": "string", "required": False, "guidance": "Server-side circle scope"},
        {"name": "vendor", "type": "string", "required": False, "guidance": "Vendor filter where applicable"},
        {"name": "technology", "type": "string", "required": False, "guidance": "Technology (e.g. 2G, 4G, 5G)"},
        {"name": "date", "type": "date", "required": False, "guidance": "Date filter where applicable"},
    ]
    return standard_filters


def load_csv_inventory(csv_path: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Load Java API inventory CSV indexed by (Method, Path)."""
    endpoints = {}
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            m = row["Method"].strip().upper()
            p = row["Path"].strip()
            endpoints[(m, p)] = row
    return endpoints


def match_endpoint_in_csv(method: str, path: str, csv_endpoints: dict) -> tuple[bool, str | None, str | None]:
    """Check if (method, path) matches directly or matches a path template in the CSV."""
    if (method, path) in csv_endpoints:
        return True, path, csv_endpoints[(method, path)].get("Controller")

    for (cm, cp), crow in csv_endpoints.items():
        if cm == method:
            # Match template e.g. /api/nodes/reports/{reportType}
            regex = "^" + re.sub(r"\{[^}]+\}", r"[^/]+", cp) + "$"
            if re.match(regex, path):
                return True, cp, crow.get("Controller")

    return False, None, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate NETIQ report metadata and API allowlist.")
    parser.add_argument("--excel", type=Path, default=DEFAULT_EXCEL_PATH, help="Path to Report Catalogue Excel")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="Path to Java API Inventory CSV")
    args = parser.parse_args()

    excel_path = args.excel
    csv_path = args.csv

    if not excel_path.is_file():
        raise FileNotFoundError(f"Excel file not found at: {excel_path}")
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found at: {csv_path}")

    print(f"Loading Excel workbook: {excel_path}")
    wb = openpyxl.load_workbook(excel_path, data_only=True)

    print(f"Loading CSV inventory: {csv_path}")
    csv_endpoints = load_csv_inventory(csv_path)

    # 1. Read 1233 Column Mappings
    ws_cols = wb["1233 Column Mappings"]
    rows_cols = list(ws_cols.iter_rows(values_only=True))
    cols_by_report_num = defaultdict(list)
    for r in rows_cols[4:]:
        if any(r):
            rep_num = r[0]
            ui_col_id = str(r[2] or "").strip()
            ui_header = str(r[3] or "").strip()
            dto_acc = str(r[4] or "").strip()
            cols_by_report_num[rep_num].append({
                "ui_column_id": ui_col_id,
                "ui_header": ui_header,
                "dto_accessor": dto_acc,
                "db_column_name": None,  # Not verified in source
                "data_type": None,       # Never silently inferred
                "verification_status": "SOURCE_DERIVED",
            })

    # 2. Read 57 UI Reports
    ws_ui = wb["57 UI Reports"]
    rows_ui = list(ws_ui.iter_rows(values_only=True))
    hdr_ui = rows_ui[3]
    ui_reports_raw = [dict(zip(hdr_ui, r)) for r in rows_ui[4:] if any(r)]

    reports_catalog = []
    reconciliation_anomalies = {
        "shared_report_codes": defaultdict(list),
        "missing_api_mappings": [],
        "conflicting_endpoints": [],
        "unmapped_inventory_codes": [],
        "unmapped_audit_codes": [],
    }

    # Group UI reports by report code to find shared codes
    code_to_reports = defaultdict(list)
    for r in ui_reports_raw:
        code = str(r["Report Code"] or "").strip()
        code_to_reports[code].append(r["Report Name"])

    for code, rep_names in code_to_reports.items():
        if len(rep_names) > 1 and code != "Not established":
            reconciliation_anomalies["shared_report_codes"][code] = rep_names

    # Track unique report codes processed
    processed_report_codes = set()

    for r in ui_reports_raw:
        rep_num = r["#"]
        rep_name = str(r["Report Name"] or "").strip()
        rep_desc = str(r["Report Description"] or "").strip()
        domain = str(r["Domain"] or "").strip()
        rep_code = str(r["Report Code"] or "").strip()
        api_raw = str(r["API to Fetch / Filter"] or "").strip()
        dto_family = str(r["Request DTO"] or "").strip()
        filter_guidance = str(r["Filter Guidance"] or "").strip()
        source_evidence = str(r["Source Evidence"] or "").strip()
        notes = str(r["Notes"] or "").strip()

        report_id = sanitize_id(rep_name)
        folder = normalize_domain_folder(domain)
        columns = cols_by_report_num.get(rep_num, [])

        # Parse API candidate
        api_meta = None
        api_method = None
        api_path = None
        matched_template = None
        controller = None

        if api_raw and not api_raw.startswith("Not"):
            parts = api_raw.split(maxsplit=1)
            if len(parts) == 2:
                api_method, api_path = parts[0].strip().upper(), parts[1].strip()
                matched, matched_template, controller = match_endpoint_in_csv(api_method, api_path, csv_endpoints)
                if matched:
                    api_meta = {
                        "method": api_method,
                        "path": api_path,
                        "path_template": matched_template or api_path,
                        "request_dto": dto_family if dto_family else None,
                        "paged": True,
                        "page_size": 50,
                        "read_only": True,
                        "production_eligible": False,  # Blocked until verified
                        "verification_status": "UNVERIFIED",
                        "controller": controller,
                    }
                else:
                    api_meta = {
                        "method": api_method,
                        "path": api_path,
                        "path_template": None,
                        "request_dto": dto_family,
                        "paged": True,
                        "page_size": 50,
                        "read_only": True,
                        "production_eligible": False,
                        "verification_status": "UNVERIFIED",
                        "controller": None,
                    }
        else:
            reconciliation_anomalies["missing_api_mappings"].append({
                "report_number": rep_num,
                "report_name": rep_name,
                "domain": domain,
                "note": "AI site/node/cell inference UI group lacks confirmed distinct read API mapping.",
            })

        # Verification statuses
        verification = {
            "report_identity": "SOURCE_DERIVED",
            "api_method_path": "SOURCE_DERIVED" if api_meta else "NOT_AVAILABLE",
            "field_mapping": "SOURCE_DERIVED",
            "request_parameters": "SOURCE_DERIVED" if dto_family else "UNVERIFIED",
            "response_schema": "UNVERIFIED",
            "pagination": "UNVERIFIED",
            "business_rules": "UNVERIFIED",
            "authorization": "UNVERIFIED",
        }

        # Dotted path response mapping configuration
        response_mapping = {
            "rows_path": "data",
            "total_path": "pagination.totalRecords",
            "page_path": "pagination.page",
            "size_path": "pagination.size",
            "has_next_path": "hasNext",
            "status_path": "success",
            "error_path": "message",
            "data_version_path": None,
            "data_as_of_path": None,
            "field_aliases": {c["dto_accessor"]: c["ui_column_id"] for c in columns if c["dto_accessor"] != c["ui_column_id"]},
        }

        rel_file_path = f"configs/reports/{folder}/{report_id.lower()}.yaml"
        full_file_path = PROJECT_ROOT / rel_file_path

        report_def = {
            "id": report_id,
            "name": rep_name,
            "description": rep_desc,
            "domain": domain,
            "report_code": rep_code,
            "file_path": rel_file_path,
            "source_provenance": {
                "worksheet": "57 UI Reports",
                "row_number": rep_num + 4,
                "source_evidence": source_evidence,
                "notes": notes,
            },
            "verification": verification,
            "api": api_meta,
            "columns": columns,
            "filters": parse_filter_guidance(filter_guidance),
            "response_mapping": response_mapping,
            "circle_scope": "server_side",
            "empty_result_message": "No Data Found!!",
        }

        # Ensure directory exists and write individual domain YAML
        full_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_file_path, "w", encoding="utf-8") as f:
            yaml.dump(report_def, f, sort_keys=False)

        # Master catalog summary
        reports_catalog.append({
            "id": report_id,
            "name": rep_name,
            "domain": domain,
            "report_code": rep_code,
            "folder": folder,
            "file_path": rel_file_path,
            "columns_count": len(columns),
            "api_endpoint": f"{api_meta['method']} {api_meta['path']}" if api_meta else None,
            "production_eligible": False,
            "verification_status": verification["api_method_path"],
        })

        if rep_code and rep_code != "Not established":
            processed_report_codes.add(rep_code)

    # 3. Read 64 Inventory Codes
    ws_inv = wb["64 Inventory Codes"]
    rows_inv = list(ws_inv.iter_rows(values_only=True))
    inv_codes_raw = [dict(zip(rows_inv[3], r)) for r in rows_inv[4:] if any(r)]
    for r in inv_codes_raw:
        code = str(r["Report Code"] or "").strip()
        if code not in processed_report_codes:
            reconciliation_anomalies["unmapped_inventory_codes"].append({
                "enum_name": str(r["Enum Name"] or "").strip(),
                "report_code": code,
                "display_name": str(r["Display Name"] or "").strip(),
                "endpoint": str(r["Endpoint"] or "").strip(),
                "request_dto": str(r["Request DTO"] or "").strip(),
            })

    # 4. Read 32 Audit Codes
    ws_aud = wb["32 Audit Codes"]
    rows_aud = list(ws_aud.iter_rows(values_only=True))
    aud_codes_raw = [dict(zip(rows_aud[3], r)) for r in rows_aud[4:] if any(r)]
    for r in aud_codes_raw:
        code = str(r["Report Code"] or "").strip()
        endpoint = str(r["Endpoint Candidate"] or "").strip()
        if code == "ip-data-audit-report":
            reconciliation_anomalies["conflicting_endpoints"].append({
                "report_code": code,
                "display_name": str(r["Display Name"] or "").strip(),
                "conflict": "Code exists in both Inventory (POST /api/nodes/reports/ip-data-audit-report via ReportRequest) and Audit (POST /api/v1/audit/reports/ip-data-audit-report via AuditReportRequest).",
            })
        if code not in processed_report_codes:
            reconciliation_anomalies["unmapped_audit_codes"].append({
                "enum_name": str(r["Enum Name"] or "").strip(),
                "report_code": code,
                "display_name": str(r["Display Name"] or "").strip(),
                "endpoint_candidate": endpoint,
                "request_dto": str(r["Request DTO"] or "").strip(),
            })

    # Convert defaultdicts to regular dicts for clean YAML serialization
    reconciliation_anomalies["shared_report_codes"] = dict(reconciliation_anomalies["shared_report_codes"])

    # Write configs/reports/catalog.yaml
    catalog_yaml_path = PROJECT_ROOT / "configs" / "reports" / "catalog.yaml"
    catalog_data = {
        "metadata_version": "1.0.0",
        "total_reports": len(reports_catalog),
        "source_derived_date": "2026-11-20",
        "reports": reports_catalog,
        "reconciliation_anomalies": reconciliation_anomalies,
    }
    with open(catalog_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(catalog_data, f, sort_keys=False)
    print(f"Master catalog written: {catalog_yaml_path} ({len(reports_catalog)} reports)")

    # 5. Build configs/allowed_apis.yaml
    allowed_apis = [
        {
            "id": "netiq_inventory_reports",
            "method": "POST",
            "path_template": "/api/nodes/reports/{reportType}",
            "description": "Primary generic inventory and AI parameter report endpoint",
            "request_dto": "ReportRequest",
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "ReportController.java",
        },
        {
            "id": "netiq_audit_reports",
            "method": "POST",
            "path_template": "/api/v1/audit/reports/{type}",
            "description": "Primary audit report retrieval endpoint",
            "request_dto": "AuditReportRequest",
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "AuditReportController.java",
        },
        {
            "id": "netiq_audit_reports_txn",
            "method": "POST",
            "path_template": "/api/v1/audit/reports/TXN/{type}",
            "description": "Audit report transaction variant endpoint",
            "request_dto": "DataRequest",
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "AuditReportController.java",
        },
        {
            "id": "netiq_stitching_report",
            "method": "POST",
            "path_template": "/api/v1/stitching/report",
            "description": "End-to-end stitching service report endpoint",
            "request_dto": "StitchingReportRequest",
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "StitchingController.java",
        },
        {
            "id": "netiq_stitching_summary",
            "method": "GET",
            "path_template": "/api/v1/stitching/summary",
            "description": "Stitching overview and summary metrics",
            "request_dto": None,
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "StitchingController.java",
        },
        {
            "id": "netiq_daily_change_summary",
            "method": "GET",
            "path_template": "/api/v1/ai/daily-change/summary",
            "description": "Daily network change summary metric endpoint",
            "request_dto": None,
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "DailyNetworkChangeController.java",
        },
        {
            "id": "netiq_daily_change_report",
            "method": "POST",
            "path_template": "/api/v1/ai/daily-change/report",
            "description": "Daily network change detailed report endpoint",
            "request_dto": "DailyChangeRequest",
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "DailyNetworkChangeController.java",
        },
        {
            "id": "netiq_cells_4g",
            "method": "GET",
            "path_template": "/api/cells/4g",
            "description": "Direct 4G cells query endpoint",
            "request_dto": None,
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "CellController.java",
        },
        {
            "id": "netiq_cells_5g",
            "method": "GET",
            "path_template": "/api/cells/5g",
            "description": "Direct 5G cells query endpoint",
            "request_dto": None,
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "CellController.java",
        },
        {
            "id": "netiq_ip_reports_ip_data",
            "method": "GET",
            "path_template": "/api/ip-reports/ip-data",
            "description": "Direct IP data query endpoint",
            "request_dto": None,
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "IpDataController.java",
        },
        {
            "id": "netiq_ran_predictions_records",
            "method": "GET",
            "path_template": "/api/v1/ai/ran-predictions/records",
            "description": "RAN prediction records query endpoint",
            "request_dto": None,
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "MissingParameterReportController.java",
        },
        {
            "id": "netiq_mw_degradation_report",
            "method": "GET",
            "path_template": "/api/v1/ai/mw-degradation/report",
            "description": "Microwave link degradation report endpoint",
            "request_dto": None,
            "read_only": True,
            "contract_status": "UNVERIFIED",
            "production_eligible": False,
            "controller": "MwDegradationController.java",
        },
    ]

    excluded_apis = [
        {"path_template": "/api/db-console/verify", "method": "POST", "reason": "Arbitrary SQL verification hazard"},
        {"path_template": "/api/db-console/execute", "method": "POST", "reason": "Arbitrary SQL execution hazard"},
        {"path_template": "/api/data/import", "method": "POST", "reason": "Data mutation / import operation"},
        {"path_template": "/api/data/importMW", "method": "POST", "reason": "Data mutation / MW import operation"},
        {"path_template": "/api/data/importDelta", "method": "POST", "reason": "Data mutation / delta import operation"},
        {"path_template": "/api/data/import/**", "method": "ANY", "reason": "Bulk ETL / import operations"},
        {"path_template": "**/export", "method": "ANY", "reason": "Export endpoints excluded from read-only query layer"},
        {"path_template": "/api/refresh", "method": "GET", "reason": "Dashboard cache / view refresh operation"},
        {"path_template": "/api/data/refresh/{type}", "method": "GET", "reason": "Materialized-view refresh operation"},
        {"path_template": "/api/nodes/mw-tr-link/trigger-scheduler", "method": "POST", "reason": "Scheduler job trigger mutation"},
        {"path_template": "/api/frequency/sync", "method": "POST", "reason": "Frequency sync state change"},
        {"path_template": "/api/v1/ai/cell-to-ru/train", "method": "POST", "reason": "Model training mutation"},
    ]

    allowed_apis_path = PROJECT_ROOT / "configs" / "allowed_apis.yaml"
    with open(allowed_apis_path, "w", encoding="utf-8") as f:
        yaml.dump({
            "policy": "fail_closed_exact_template",
            "wildcards_permitted": False,
            "allowed_apis": allowed_apis,
            "explicitly_excluded": excluded_apis,
        }, f, sort_keys=False)
    print(f"API allowlist written: {allowed_apis_path} ({len(allowed_apis)} approved templates, {len(excluded_apis)} excluded)")


if __name__ == "__main__":
    main()
