import copy

import pytest

from scripts.analyze_semantic_review_agreement import analyze, cohen_kappa


def packet(reviewer, decisions=("approve", "approve")):
    tasks = []
    for index, decision in enumerate(decisions):
        tasks.append(
            {
                "split": "iid_core",
                "source_path": f"task_{index}/problem0.bddl",
                "review": {
                    "source_to_compiled_goal": True,
                    "action_preconditions": True,
                    "action_effects": True,
                    "trace_plausibility_at_declared_abstraction": True,
                    "selective_closed_world_assumptions": True,
                    "decision": decision,
                    "reviewer": reviewer,
                    "date": "2026-09-15",
                    "notes": "",
                },
            }
        )
    return {
        "evidence_status": "completed_independent_review",
        "packet_version": "test-v1",
        "generic_domain_version": "domain-v1",
        "split_version": "split-v1",
        "tasks": tasks,
    }


def test_agreement_report_is_paired_by_task_and_field():
    report = analyze(packet("A"), packet("B", ("approve", "revise")))
    assert report["task_count"] == 2
    assert report["per_field"]["decision"]["agreement_rate"] == 0.5
    assert report["disagreement_count"] == 1
    assert report["disagreements"][0]["task_id"].endswith("task_1/problem0.bddl")


def test_unsigned_or_incomplete_packet_fails_closed():
    unsigned = packet("A")
    unsigned["evidence_status"] = "unsigned_independent_review_packet"
    with pytest.raises(ValueError, match="not completed human review evidence"):
        analyze(unsigned, packet("B"))

    incomplete = packet("A")
    incomplete["tasks"][0]["review"]["action_effects"] = None
    with pytest.raises(ValueError, match="action_effects"):
        analyze(incomplete, packet("B"))


def test_same_reviewer_is_not_independent():
    with pytest.raises(ValueError, match="different people"):
        analyze(packet("A"), packet("A"))


def test_kappa_handles_perfect_single_class_agreement_without_infinity():
    assert cohen_kappa([True, True], [True, True]) is None


def test_packet_version_drift_is_rejected():
    right = copy.deepcopy(packet("B"))
    right["split_version"] = "split-v2"
    with pytest.raises(ValueError, match="split_version"):
        analyze(packet("A"), right)
