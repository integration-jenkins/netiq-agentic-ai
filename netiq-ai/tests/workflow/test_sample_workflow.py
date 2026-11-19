"""Sample workflow test: every sample question names a valid route."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_sample_questions_have_valid_routes():
    lines = (ROOT / "tests" / "datasets" / "sample_questions.jsonl").read_text().splitlines()
    for line in filter(None, lines):
        assert json.loads(line)["expected_route"] in {"api", "knowledge", "sql"}
