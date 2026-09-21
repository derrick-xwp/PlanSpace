import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from scripts.analyze_semantic_review_agreement import analyze


SCRIPT = Path(__file__).parents[1] / "paper" / "scripts" / "generate_human_review_data.py"
SPEC = importlib.util.spec_from_file_location("generate_human_review_data", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def reviewer_packet(name: str, *, revise_last: bool = False) -> dict:
    tasks = []
    for index in range(30):
        decision = "revise" if revise_last and index == 29 else "approve"
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


def install_complete_review(directory: Path) -> None:
    left = reviewer_packet("Reviewer A")
    right = reviewer_packet("Reviewer B", revise_last=True)
    write(directory / "semantic_review_reviewer_a_v0_3.json", left)
    write(directory / "semantic_review_reviewer_b_v0_3.json", right)
    write(directory / "semantic_review_agreement_v0_3.json", analyze(left, right))
    agreement_path = directory / "semantic_review_agreement_v0_3.json"
    disagreement = analyze(left, right)["disagreements"][0]
    write(
        directory / "semantic_review_adjudication_v0_3.json",
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
                    "rationale": "The frozen source supports approval.",
                }
            ],
        },
    )

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
        "evidence_status": "pending_independent_novel_valid_review",
        "allowed_classifications": list(MODULE.CLASSIFICATION_MACROS),
        "cases": copy.deepcopy(cases),
    }
    reviewed = copy.deepcopy(frozen)
    reviewed["evidence_status"] = "completed_human_outside_family_audit"
    classifications = list(MODULE.CLASSIFICATION_MACROS)[:2]
    for case, classification in zip(reviewed["cases"], classifications):
        case["review"] = {
            "semantically_valid_at_declared_abstraction": True,
            "should_expand_constructed_family": classification.endswith("coverage_miss"),
            "classification": classification,
            "reviewer": "Reviewer C",
            "date": "2026-09-15",
            "notes": "",
        }
    write(directory / "novel_valid_audit_v0_1.json", frozen)
    write(directory / "novel_valid_reviewed_v0_1.json", reviewed)


def test_pending_review_emits_explicit_zero_status(tmp_path: Path) -> None:
    text = MODULE.build_macros(tmp_path)
    assert r"\newcommand{\HumanReviewEvidenceReady}{0}" in text
    assert r"\newcommand{\HumanReviewAgreementRows}{}" in text


def test_partial_review_fails_closed(tmp_path: Path) -> None:
    write(tmp_path / MODULE.REQUIRED[0], {})
    with pytest.raises(FileNotFoundError, match="partial human-review evidence"):
        MODULE.build_macros(tmp_path)


def test_complete_review_emits_agreement_and_classification_counts(tmp_path: Path) -> None:
    install_complete_review(tmp_path)
    text = MODULE.build_macros(tmp_path)
    assert r"\newcommand{\HumanReviewEvidenceReady}{1}" in text
    assert "Overall decision & 96.7 & 0.000" in text
    assert r"\newcommand{\HumanNovelValidCount}{1}" in text
    assert r"\newcommand{\HumanNovelCoverageMissCount}{1}" in text
