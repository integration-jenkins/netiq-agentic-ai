"""Unit tests for report metadata catalog loading and verification status enforcement."""

from src.settings.loader import load_catalog_config, load_report_definition


def test_catalog_loads_successfully():
    catalog = load_catalog_config()
    assert "reports" in catalog
    assert len(catalog["reports"]) >= 57
    assert "reconciliation_anomalies" in catalog


def test_individual_reports_loadable():
    # Test loading sample key reports across domains
    ran_cell = load_report_definition("RAN_CELL_4G")
    assert ran_cell["id"] == "RAN_CELL_4G"
    assert ran_cell["domain"] == "RAN"
    assert len(ran_cell["columns"]) == 28
    assert ran_cell["verification"]["report_identity"] == "SOURCE_DERIVED"
    assert ran_cell["verification"]["response_schema"] == "UNVERIFIED"

    mw_node = load_report_definition("MW_UBR_NODE_INVENTORY")
    assert mw_node["domain"] == "MW / UBR"
    assert len(mw_node["columns"]) == 15


def test_reconciliation_anomalies_recorded():
    catalog = load_catalog_config()
    anomalies = catalog["reconciliation_anomalies"]
    # Shared code node-report must be noted
    assert "node-report" in anomalies["shared_report_codes"]
    # Reports without API mappings (e.g. AI site/node/cell inference)
    missing_apis = anomalies["missing_api_mappings"]
    assert len(missing_apis) >= 3
    # Conflicting endpoint for ip-data-audit-report must be identified
    conflicts = anomalies["conflicting_endpoints"]
    assert any(c["report_code"] == "ip-data-audit-report" for c in conflicts)
