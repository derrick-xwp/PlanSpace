import csv
from pathlib import Path

import pytest

from scripts.apply_semantic_review_adjudication_form import apply
from scripts.export_semantic_review_adjudication_form import export


def report() -> dict:
    return {
        "disagreements": [
            {
                "task_id": "iid_core::task/problem0.bddl",
                "field": "decision",
                "reviewer_a": "approve",
                "reviewer_b": "revise",
            }
        ]
    }


def completed_rows(path: Path) -> list[dict[str, str]]:
    export(report(), path)
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0].update(
        {
            "adjudicated_value": "approve",
            "adjudicator": "Reviewer C",
            "date": "2026-09-15",
            "rationale": "The frozen source and abstraction support approval.",
        }
    )
    return rows


def test_adjudication_preserves_labels_and_freezes_resolution(tmp_path: Path) -> None:
    result = apply(report(), completed_rows(tmp_path / "form.csv"), "sha256")
    assert result["record_count"] == 1
    assert result["records"][0]["reviewer_b"] == "revise"
    assert result["records"][0]["adjudicated_value"] == "approve"


def test_adjudication_rejects_changed_independent_label(tmp_path: Path) -> None:
    rows = completed_rows(tmp_path / "form.csv")
    rows[0]["reviewer_b_value"] = "approve"
    with pytest.raises(ValueError, match="frozen reviewer labels changed"):
        apply(report(), rows, "sha256")


def test_adjudication_requires_rationale(tmp_path: Path) -> None:
    rows = completed_rows(tmp_path / "form.csv")
    rows[0]["rationale"] = ""
    with pytest.raises(ValueError, match="lacks date or rationale"):
        apply(report(), rows, "sha256")
