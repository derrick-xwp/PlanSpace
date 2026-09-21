import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.analyze_semantic_review_agreement import analyze
from scripts.verify_v02_release import verify_human_review


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def reviewer_packet(name: str, *, last_decision: str = "approve") -> dict:
    tasks = []
    for index in range(30):
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
                    "decision": last_decision if index == 29 else "approve",
                    "reviewer": name,
                    "date": "2026-09-15",
                    "notes": "",
                },
            }
        )
    return {
        "evidence_status": "completed_independent_review",
        "packet_version": "packet-v1",
        "generic_domain_version": "domain-v1",
        "split_version": "split-v1",
        "tasks": tasks,
    }


def install_review_artifacts(directory: Path) -> None:
    left = reviewer_packet("Reviewer A")
    right = reviewer_packet("Reviewer B")
    write(directory / "semantic_review_reviewer_a_v0_3.json", left)
    write(directory / "semantic_review_reviewer_b_v0_3.json", right)
    write(directory / "semantic_review_agreement_v0_3.json", analyze(left, right))

    cases = [
        {
            "audit_id": f"case-{index}",
            "source_path": f"task-{index}/problem0.bddl",
            "source_sha256": f"hash-{index}",
            "plan": [f"action-{index}"],
        }
        for index in range(2)
    ]
    frozen = {
        "evidence_status": "pending_human_classification",
        "allowed_classifications": [
            "valid_novel_or_nonminimal_plan",
            "constructed_family_coverage_miss",
            "action_semantics_or_evaluator_issue",
            "not_semantically_valid",
        ],
        "cases": copy.deepcopy(cases),
    }
    reviewed = copy.deepcopy(frozen)
    reviewed["evidence_status"] = "completed_human_outside_family_audit"
    for case in reviewed["cases"]:
        case["review"] = {
            "semantically_valid_at_declared_abstraction": True,
            "should_expand_constructed_family": False,
            "classification": "valid_novel_or_nonminimal_plan",
            "reviewer": "Reviewer C",
            "date": "2026-09-15",
            "notes": "",
        }
    write(directory / "novel_valid_audit_v0_1.json", frozen)
    write(directory / "novel_valid_reviewed_v0_1.json", reviewed)


def test_human_review_gate_recomputes_and_accepts_complete_evidence(tmp_path: Path) -> None:
    install_review_artifacts(tmp_path)
    verify_human_review(tmp_path)


def test_human_review_gate_rejects_tampered_agreement(tmp_path: Path) -> None:
    install_review_artifacts(tmp_path)
    path = tmp_path / "semantic_review_agreement_v0_3.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["disagreement_count"] = 99
    write(path, report)
    with pytest.raises(AssertionError):
        verify_human_review(tmp_path)


def test_completed_but_negative_review_does_not_release(tmp_path: Path) -> None:
    install_review_artifacts(tmp_path)
    left = reviewer_packet("Reviewer A", last_decision="revise")
    right = reviewer_packet("Reviewer B", last_decision="revise")
    write(tmp_path / "semantic_review_reviewer_a_v0_3.json", left)
    write(tmp_path / "semantic_review_reviewer_b_v0_3.json", right)
    write(tmp_path / "semantic_review_agreement_v0_3.json", analyze(left, right))
    with pytest.raises(AssertionError, match="unresolved non-approval"):
        verify_human_review(tmp_path)


def test_disagreement_requires_frozen_positive_adjudication(tmp_path: Path) -> None:
    install_review_artifacts(tmp_path)
    left = reviewer_packet("Reviewer A")
    right = reviewer_packet("Reviewer B", last_decision="revise")
    agreement_path = tmp_path / "semantic_review_agreement_v0_3.json"
    write(tmp_path / "semantic_review_reviewer_a_v0_3.json", left)
    write(tmp_path / "semantic_review_reviewer_b_v0_3.json", right)
    report = analyze(left, right)
    write(agreement_path, report)
    with pytest.raises(AssertionError):
        verify_human_review(tmp_path)

    disagreement = report["disagreements"][0]
    write(
        tmp_path / "semantic_review_adjudication_v0_3.json",
        {
            "evidence_status": "completed_semantic_review_adjudication",
            "agreement_sha256": hashlib.sha256(agreement_path.read_bytes()).hexdigest(),
            "record_count": 1,
            "records": [
                {
                    **disagreement,
                    "adjudicated_value": "approve",
                    "adjudicator": "Reviewer C",
                    "date": "2026-09-15",
                    "rationale": "Source goal and declared abstraction support approval.",
                }
            ],
        },
    )
    verify_human_review(tmp_path)
