import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXPORT = load("export_novel_review", ROOT / "scripts" / "export_novel_valid_review_form.py")
APPLY = load("apply_novel_review", ROOT / "scripts" / "apply_novel_valid_review_form.py")


def packet():
    return {
        "evidence_status": "pending_human_classification",
        "allowed_classifications": ["valid_novel_or_nonminimal_plan", "not_semantically_valid"],
        "cases": [
            {
                "audit_id": "case-1",
                "source_path": "task/problem0.bddl",
                "source_sha256": "abc",
                "plan": ["open::door"],
                "review": {},
            }
        ],
    }


def completed_rows():
    rows = EXPORT.export_rows(packet())
    rows[0].update(
        {
            "semantically_valid_at_declared_abstraction": "yes",
            "should_expand_constructed_family": "no",
            "classification": "valid_novel_or_nonminimal_plan",
            "reviewer": "Reviewer A",
            "date": "2026-09-15",
        }
    )
    return rows


def test_apply_form_accepts_complete_frozen_review():
    result = APPLY.apply_form(packet(), completed_rows())
    assert result["evidence_status"] == "completed_human_outside_family_audit"
    assert result["cases"][0]["review"]["semantically_valid_at_declared_abstraction"] is True


def test_apply_form_rejects_plan_drift():
    rows = completed_rows()
    rows[0]["plan_json"] = json.dumps(["close::door"], separators=(",", ":"))
    with pytest.raises(ValueError, match="metadata mismatch"):
        APPLY.apply_form(packet(), rows)


def test_apply_form_rejects_invalid_classification():
    rows = completed_rows()
    rows[0]["classification"] = "looks_good"
    with pytest.raises(ValueError, match="invalid classification"):
        APPLY.apply_form(packet(), rows)
