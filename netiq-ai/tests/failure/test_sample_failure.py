"""Sample failure test: 'No Data Found!!' is an empty result, not an error."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_no_data_fixture_is_empty_not_error():
    resp = json.loads((ROOT / "data" / "fixtures" / "sample_no_data_response.json").read_text())
    assert resp["data"] == []
    assert resp["message"] == "No Data Found!!"
