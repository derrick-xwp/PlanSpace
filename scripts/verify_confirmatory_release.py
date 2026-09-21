#!/usr/bin/env python3
"""Fail closed when the confirmatory experiment bundle is incomplete."""

from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

MODELS = {
    "qwen3_8b": (
        "Qwen/Qwen3-8B",
        "b968826d9c46dd6066d109eabc6255188de91218",
    ),
    "qwen3_4b": (
        "Qwen/Qwen3-4B",
        "1cfa9a7208912126459214e8b04321603b3df60c",
    ),
    "phi4_mini": (
        "microsoft/Phi-4-mini-instruct",
        "cfbefacb99257ffa30c83adab238a50856ac3083",
    ),
}


def load(name: str) -> dict:
    path = ARTIFACTS / name
    if not path.is_file():
        raise AssertionError(f"missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_primary(prefix: str, model_id: str, revision: str) -> None:
    raw = load(f"{prefix}_queue_100_sampling_v0_1.json")
    assert raw["model_id"] == model_id
    assert raw["model_revision"] == revision
    assert raw["summary"]["completed_task_count"] == 100
    assert raw["summary"]["sample_count"] == 500
    assert len(raw["tasks"]) == 100
    assert sum(len(task["samples"]) for task in raw["tasks"]) == 500

    enriched = load(f"{prefix}_queue_100_enriched_v0_1.json")
    assert enriched["model_id"] == model_id
    assert enriched["model_revision"] == revision
    assert enriched["summary"]["completed_task_count"] == 100
    assert enriched["summary"]["sample_count"] == 500
    assert len(enriched["tasks"]) == 100
    required_sample_fields = {
        "partial_order_match",
        "matched_reference_family_indices",
        "normalized_cost_regret",
    }
    for task in enriched["tasks"]:
        assert "reference_family_coverage" in task["metrics"]
        for sample in task["samples"]:
            assert required_sample_fields <= sample.keys()

    analysis = load(f"{prefix}_queue_100_analysis_v0_1.json")
    assert analysis["model_id"] == model_id
    assert analysis["model_revision"] == revision
    assert analysis["bootstrap"]["trials"] == 10_000
    assert sum(analysis["failure_counts"].values()) == 500
    split_counts = analysis["strata"]["structural_split"]
    assert sum(item["task_count"] for item in split_counts.values()) == 100


def verify_retries(prefix: str, model_id: str) -> None:
    queue = load(f"{prefix}_truncation_retry_queue_v0_1.json")
    selected = queue["selected_count"]
    assert selected == len(queue["records"])
    retry = load(f"{prefix}_truncation_retry_512_v0_1.json")
    assert retry["model_id"] == model_id
    assert retry["summary"]["completed_task_count"] == selected
    assert retry["summary"]["sample_count"] == selected * 5
    assert len(retry["tasks"]) == selected
    assert sum(len(task["samples"]) for task in retry["tasks"]) == selected * 5


def main() -> None:
    for prefix, (model_id, revision) in MODELS.items():
        verify_primary(prefix, model_id, revision)
        verify_retries(prefix, model_id)

    audit = load("generic_domain_audit_100_v0_3.json")
    assert audit["summary"]["queue_task_count"] == 100
    assert audit["summary"]["all_stored_plans_validate"] is True
    assert (
        audit["summary"]["topological_orders_checked"]
        == audit["summary"]["topological_orders_valid"]
    )

    controls = load("deterministic_controls_100_v0_1.json")
    assert controls["summary"]["task_count"] == 100
    assert controls["summary"]["positive_goal_valid_rate"] == 1.0
    assert controls["summary"]["deletion_negative_rejection_rate"] == 1.0

    comparison = load("three_model_comparison_v0_1.json")
    assert set(comparison["aggregate"]) == {
        model_id for model_id, _ in MODELS.values()
    }
    assert len(comparison["paired_comparisons"]) == 3

    truncation = load("truncation_retry_analysis_v0_1.json")
    assert {row["model_id"] for row in truncation["models"]} == {
        model_id for model_id, _ in MODELS.values()
    }

    sampling = load("sampling_curve_analysis_v0_1.json")
    assert sampling["bootstrap"]["unit"] == "task"
    assert sampling["bootstrap"]["trials"] == 10_000
    assert {row["model_id"] for row in sampling["models"]} == {
        model_id for model_id, _ in MODELS.values()
    }
    for row in sampling["models"]:
        assert row["task_count"] == 100
        assert row["samples_per_task"] == 5
        assert [point["k"] for point in row["points"]] == [1, 2, 3, 4, 5]

    review = load("semantic_review_packet_30_v0_3.json")
    assert review["task_count"] == 30 == len(review["tasks"])
    assert all(task["automatic_replay_valid"] for task in review["tasks"])
    assert review["evidence_status"] == "unsigned_independent_review_packet"
    semantic_form = ARTIFACTS / "semantic_review_form_30_v0_3.csv"
    assert semantic_form.is_file()
    with semantic_form.open(encoding="utf-8", newline="") as handle:
        semantic_rows = list(csv.DictReader(handle))
    assert {row["task_id"] for row in semantic_rows} == {
        f"{task['split']}::{task['source_path']}" for task in review["tasks"]
    }
    assert all(
        not row[field]
        for row in semantic_rows
        for field in (
            "source_to_compiled_goal",
            "action_preconditions",
            "action_effects",
            "trace_plausibility_at_declared_abstraction",
            "selective_closed_world_assumptions",
            "decision",
            "reviewer",
            "date",
            "notes",
        )
    )

    handoff = ARTIFACTS / "PlanSpace_semantic_review_handoff_v0_3.zip"
    handoff_checksum = ARTIFACTS / "PlanSpace_semantic_review_handoff_v0_3.zip.sha256"
    assert handoff.is_file() and handoff_checksum.is_file()
    with zipfile.ZipFile(handoff) as archive:
        assert set(archive.namelist()) == {
            "SEMANTIC_REVIEW_HANDOFF_ZH.md",
            "SEMANTIC_REVIEW_WORKFLOW.md",
            "SEMANTIC_REVIEW_PACKET_30_V0_3.md",
            "ACTION_ABSTRACTION_CONTRACT.md",
            "semantic_review_form_30_v0_3.csv",
            "NOVEL_VALID_AUDIT_V0_1.md",
            "novel_valid_review_form_v0_1.csv",
        }
    expected_digest = handoff_checksum.read_text(encoding="utf-8").split()[0]
    assert sha256(handoff.read_bytes()).hexdigest() == expected_digest

    coverage = load("bounded_family_coverage_v0_1.json")
    assert coverage["summary"]["exhaustively_analyzed_task_count"] == 74
    assert coverage["summary"]["bounded_valid_plan_count"] == 2507
    assert coverage["summary"]["bounded_valid_plan_covered_count"] == 2471
    assert coverage["summary"]["tasks_with_full_bounded_coverage"] == 73
    assert all(
        task["search_exhaustive"]
        and task["family_order_enumeration_exhaustive"]
        for task in coverage["tasks"]
    )

    expanded_review = load("semantic_review_packet_30_v0_3.json")
    assert expanded_review["evidence_status"] == "unsigned_independent_review_packet"
    assert expanded_review["task_count"] == 30 == len(expanded_review["tasks"])
    assert all(task["automatic_replay_valid"] for task in expanded_review["tasks"])
    split_counts = {}
    for task in expanded_review["tasks"]:
        split_counts[task["split"]] = split_counts.get(task["split"], 0) + 1
    assert set(split_counts.values()) == {6}
    assert len(split_counts) == 5

    selection = load("selection_coverage_audit_v0_1.json")
    assert selection["evidence_status"] == "descriptive_selection_coverage_audit"
    assert [row["count"] for row in selection["funnel"]] == [1016, 202, 120, 109, 100]
    assert selection["stages"]["frozen_final_queue"]["count"] == 100
    assert selection["translation_pass_not_selected_count"] == 9

    novel = load("novel_valid_audit_v0_1.json")
    assert novel["evidence_status"] == "pending_independent_novel_valid_review"
    assert novel["total_occurrence_count"] == 10
    assert novel["unique_case_count"] == 2 == len(novel["cases"])
    assert all(case["execution_result"]["valid"] for case in novel["cases"])
    assert all(case["review"]["classification"] is None for case in novel["cases"])
    review_form = ARTIFACTS / "novel_valid_review_form_v0_1.csv"
    assert review_form.is_file()
    with review_form.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["audit_id"] for row in rows} == {
        case["audit_id"] for case in novel["cases"]
    }
    assert all(
        not row[field]
        for row in rows
        for field in (
            "semantically_valid_at_declared_abstraction",
            "should_expand_constructed_family",
            "classification",
            "reviewer",
            "date",
            "notes",
        )
    )

    generated = ROOT / "paper" / "generated_confirmatory.tex"
    assert generated.is_file()
    text = generated.read_text(encoding="utf-8")
    assert "TEMPORARY LAYOUT PLACEHOLDER" not in text
    assert "Generated by paper/scripts/generate_confirmatory_data.py" in text
    print("confirmatory release verified")


if __name__ == "__main__":
    main()
