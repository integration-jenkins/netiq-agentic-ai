"""Sample benchmark placeholder: dataset is loadable and non-empty."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dataset_not_empty():
    assert (ROOT / "tests" / "datasets" / "sample_questions.jsonl").read_text().strip()
