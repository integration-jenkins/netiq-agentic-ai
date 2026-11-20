"""Validate report metadata, catalog integrity, and API allowlist consistency."""

import sys
from pathlib import Path
import re
import yaml
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.schemas.metadata import ReportDefinition, VerificationStatus


def validate_catalog() -> list[str]:
    """Validate configs/reports/catalog.yaml and all linked domain YAML files."""
    errors = []
    catalog_path = PROJECT_ROOT / "configs" / "reports" / "catalog.yaml"
    if not catalog_path.is_file():
        return [f"Catalog file missing: {catalog_path}"]

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = yaml.safe_load(f)
    except Exception as e:
        return [f"Failed to read catalog YAML: {e}"]

    reports = catalog.get("reports", [])
    if not reports:
        return ["Catalog has no reports listed"]

    allowed_statuses = {s.value for s in VerificationStatus}

    for rep in reports:
        rep_id = rep.get("id")
        rel_path = rep.get("file_path")
        if not rep_id or not rel_path:
            errors.append(f"Catalog entry missing id or file_path: {rep}")
            continue

        file_path = PROJECT_ROOT / rel_path
        if not file_path.is_file():
            errors.append(f"Referenced report file does not exist: {file_path}")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                rep_data = yaml.safe_load(f)
            
            # Validate against Pydantic schema
            parsed = ReportDefinition.model_validate(rep_data)

            # Validate verification statuses
            v = parsed.verification
            for dim, status in [
                ("report_identity", v.report_identity),
                ("api_method_path", v.api_method_path),
                ("field_mapping", v.field_mapping),
                ("request_parameters", v.request_parameters),
                ("response_schema", v.response_schema),
                ("pagination", v.pagination),
                ("business_rules", v.business_rules),
                ("authorization", v.authorization),
            ]:
                if status not in allowed_statuses:
                    errors.append(f"Report {rep_id} has invalid {dim} status: {status}")

            # Column verification
            for col in parsed.columns:
                if col.verification_status not in allowed_statuses:
                    errors.append(f"Report {rep_id} column {col.ui_column_id} has invalid status: {col.verification_status}")

        except ValidationError as ve:
            errors.append(f"Schema validation error in {file_path}: {ve}")
        except Exception as e:
            errors.append(f"Error parsing {file_path}: {e}")

    return errors


def validate_allowlist() -> list[str]:
    """Validate configs/allowed_apis.yaml."""
    errors = []
    allowlist_path = PROJECT_ROOT / "configs" / "allowed_apis.yaml"
    if not allowlist_path.is_file():
        return [f"Allowlist file missing: {allowlist_path}"]

    try:
        with open(allowlist_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return [f"Failed to read allowlist YAML: {e}"]

    allowed_apis = data.get("allowed_apis", [])
    if not allowed_apis:
        return ["Allowlist has no entries in 'allowed_apis'"]

    for api in allowed_apis:
        api_id = api.get("id")
        method = api.get("method")
        template = api.get("path_template")
        read_only = api.get("read_only")
        prod_eligible = api.get("production_eligible")

        if not api_id or not method or not template:
            errors.append(f"Malformed allowlist entry: {api}")
            continue

        if "**" in template or "*" in template:
            errors.append(f"Allowlist entry {api_id} contains forbidden wildcard in path_template: {template}")

        if not read_only:
            errors.append(f"Allowlist entry {api_id} is not marked read_only: True")

        # In Stage 1, all endpoints must be production_eligible: False
        if prod_eligible is True and api.get("contract_status") != "VERIFIED":
            errors.append(f"Allowlist entry {api_id} is marked production_eligible=True while contract is {api.get('contract_status')}")

    return errors


def main() -> None:
    print("Validating report metadata catalog...")
    catalog_errors = validate_catalog()
    if catalog_errors:
        print(f"FAILED: {len(catalog_errors)} catalog errors found:")
        for err in catalog_errors:
            print(f"  - {err}")
    else:
        print("SUCCESS: Report catalog and all domain files passed validation.")

    print("\nValidating API allowlist...")
    allowlist_errors = validate_allowlist()
    if allowlist_errors:
        print(f"FAILED: {len(allowlist_errors)} allowlist errors found:")
        for err in allowlist_errors:
            print(f"  - {err}")
    else:
        print("SUCCESS: API allowlist passed validation.")

    if catalog_errors or allowlist_errors:
        sys.exit(1)
    print("\nAll metadata validations passed successfully!")


if __name__ == "__main__":
    main()
