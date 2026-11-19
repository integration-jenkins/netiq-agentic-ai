"""Sample unit test: key config files exist (stdlib only)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_allowed_apis_file_exists():
    assert "allowed_apis" in (ROOT / "configs" / "allowed_apis.yaml").read_text()


def test_each_report_domain_has_a_sample():
    for domain in ("audit", "ftth", "mw", "ran", "wireline"):
        assert (ROOT / "configs" / "reports" / domain / "sample_report.yaml").exists()
