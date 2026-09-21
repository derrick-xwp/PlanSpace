import copy

import pytest

from scripts.analyze_semantic_review_agreement import analyze as analyze_human
from scripts.analyze_semantic_review_ai_agreement import analyze as analyze_ai
from scripts.apply_semantic_review_ai_result import apply_result


def frozen_packet():
    return {
        "evidence_status": "unsigned_independent_review_packet",
        "packet_version": "test-v1",
        "generic_domain_version": "domain-v1",
        "split_version": "split-v1",
        "tasks": [{"split": "iid_core", "source_path": "task/problem0.bddl", "review": {}}],
    }


def result(reviewer, decision="approve"):
    return {
        "reviewer": reviewer,
        "reviewer_kind": "codex_cli_ai",
        "date": "2026-09-15",
        "rows": [{
            "task_id": "iid_core::task/problem0.bddl",
            "source_path": "task/problem0.bddl",
            "split": "iid_core",
            "source_to_compiled_goal": True,
            "action_preconditions": True,
            "action_effects": True,
            "trace_plausibility_at_declared_abstraction": True,
            "selective_closed_world_assumptions": True,
            "decision": decision,
            "notes": "",
        }],
    }


def test_ai_results_are_validated_and_compared():
    left = apply_result(frozen_packet(), result("codex-a"))
    right = apply_result(frozen_packet(), result("codex-b", "revise"))
    report = analyze_ai(left, right)
    assert report["evidence_status"] == "independent_codex_cli_ai_audit_agreement"
    assert report["per_field"]["decision"]["agreement_rate"] == 0.0


def test_ai_packet_cannot_pass_human_agreement_analyzer():
    left = apply_result(frozen_packet(), result("codex-a"))
    right = apply_result(frozen_packet(), result("codex-b"))
    with pytest.raises(ValueError, match="not completed human review evidence"):
        analyze_human(left, right)


def test_ai_result_fails_closed_on_metadata_or_kind():
    bad = result("codex-a")
    bad["reviewer_kind"] = "human"
    with pytest.raises(ValueError, match="codex_cli_ai"):
        apply_result(frozen_packet(), bad)
    bad = copy.deepcopy(result("codex-a"))
    bad["rows"][0]["source_path"] = "changed"
    with pytest.raises(ValueError, match="metadata mismatch"):
        apply_result(frozen_packet(), bad)
