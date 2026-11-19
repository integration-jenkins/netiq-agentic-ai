"""Sample security test: no obvious secrets in version-controlled configs."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERN = re.compile(r"(password|secret|token)\s*:\s*\S+", re.IGNORECASE)


def test_configs_contain_no_secrets():
    for f in (ROOT / "configs").rglob("*.yaml"):
        assert not PATTERN.search(f.read_text()), f
