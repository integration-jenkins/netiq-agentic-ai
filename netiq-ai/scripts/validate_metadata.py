"""Validate report metadata, catalog integrity, and API allowlist consistency.

Architecture Role:
------------------
This script is the CI/CD and deployment verification gate for report configurations.
It ensures that all YAML files in `configs/reports/` and `configs/allowed_apis.yaml`
conform strictly to the Pydantic metadata schema (`ReportDefinition`), that no files
are missing, that all verification statuses use approved enum values, and that no
unauthorized wildcards or mutation routes exist in the allowlist.

Validation Checks:
------------------
1. Catalog Completeness: Verifies `catalog.yaml` exists and contains registered reports.
2. File Existence: Confirms every report listed in the catalog exists as a valid YAML file.
3. Schema Conformance: Validates every YAML file against `src.schemas.metadata.ReportDefinition`.
4. Verification Status Legality: Enforces that status values are strictly within:
   `SOURCE_DERIVED`, `VERIFIED`, `UNVERIFIED`, `CONFLICT`, `NOT_AVAILABLE`.
5. Allowlist Integrity: Rejects wildcards (`*`, `**`), verifies `read_only=True`, and
   verifies that unverified contracts have `production_eligible=False`.
"""

import sys
from pathlib import Path
import re
import yaml
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.schemas.metadata import ReportDefinition, VerificationStatus


def validate_catalog() -> list[str]:
    """Validate configs/reports/catalog.yaml and all linked domain YAML files.
    
    Returns:
        list[str]: List of error message strings (empty if validation succeeds).
    """
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
            
            # Validate complete report definition against Pydantic schema
            parsed = ReportDefinition.model_validate(rep_data)

            # Validate verification statuses across all 8 dimensions
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

            # Validate column mapping verification statuses
            for col in parsed.columns:
                if col.verification_status not in allowed_statuses:
                    errors.append(f"Report {rep_id} column {col.ui_column_id} has invalid status: {col.verification_status}")

        except ValidationError as ve:
            errors.append(f"Schema validation error in {file_path}: {ve}")
        except Exception as e:
            errors.append(f"Error parsing {file_path}: {e}")

    return errors


def validate_allowlist() -> list[str]:
    """Validate configs/allowed_apis.yaml.
    
    Returns:
        list[str]: List of error message strings (empty if validation succeeds).
    """
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

        # Zero wildcard check
        if "**" in template or "*" in template:
            errors.append(f"Allowlist entry {api_id} contains forbidden wildcard in path_template: {template}")

        # Read-only operation check
        if not read_only:
            errors.append(f"Allowlist entry {api_id} is not marked read_only: True")

        # Stage 1 fail-closed check: unverified contracts cannot be production_eligible
        if prod_eligible is True and api.get("contract_status") != "VERIFIED":
            errors.append(f"Allowlist entry {api_id} is marked production_eligible=True while contract is {api.get('contract_status')}")

    return errors


def main() -> None:
    """Run validation checks and exit 0 if all pass, 1 if any fail."""
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
