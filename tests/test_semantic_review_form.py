import copy

import pytest

from scripts.apply_semantic_review_form import apply_form


def packet():
    return {
        "evidence_status": "unsigned_independent_review_packet",
        "tasks": [
            {
                "split": "iid_core",
                "source_path": "task/problem0.bddl",
                "review": {
                    "source_to_compiled_goal": None,
                    "action_preconditions": None,
                    "action_effects": None,
                    "trace_plausibility_at_declared_abstraction": None,
                    "selective_closed_world_assumptions": None,
                    "decision": None,
                    "reviewer": None,
                    "date": None,
                    "notes": None,
                },
            }
        ],
    }


def row():
    return {
        "task_id": "iid_core::task/problem0.bddl",
        "source_path": "task/problem0.bddl",
        "split": "iid_core",
        "source_to_compiled_goal": "yes",
        "action_preconditions": "true",
        "action_effects": "1",
        "trace_plausibility_at_declared_abstraction": "y",
        "selective_closed_world_assumptions": "no",
        "decision": "revise",
        "reviewer": "Reviewer A",
        "date": "2026-09-15",
        "notes": "closed-world policy needs revision",
    }


def test_completed_form_is_applied_without_mutating_frozen_packet():
    frozen = packet()
    completed = apply_form(frozen, [row()])
    assert frozen["tasks"][0]["review"]["decision"] is None
    assert completed["evidence_status"] == "completed_independent_review"
    assert completed["tasks"][0]["review"]["decision"] == "revise"
    assert completed["tasks"][0]["review"]["selective_closed_world_assumptions"] is False


def test_incomplete_or_metadata_drift_fails_closed():
    bad = copy.deepcopy(row())
    bad["action_effects"] = ""
    with pytest.raises(ValueError, match="action_effects"):
        apply_form(packet(), [bad])
    bad = copy.deepcopy(row())
    bad["source_path"] = "changed"
    with pytest.raises(ValueError, match="metadata mismatch"):
        apply_form(packet(), [bad])
