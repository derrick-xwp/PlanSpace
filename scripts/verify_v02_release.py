#!/usr/bin/env python3
"""Fail closed unless the complete six-model v0.2 release is internally consistent."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

from scripts.analyze_semantic_review_agreement import (
    BOOLEAN_FIELDS,
    REVIEW_FIELDS,
    analyze as analyze_semantic_review,
    task_id as semantic_task_id,
)
from scripts.process_model_matrix_v0_2 import validate_raw_record
from scripts.verify_model_matrix_v0_2 import verify_matrix


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing v0.2 artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_human_review(result_dir: Path) -> None:
    reviewer_a = load(result_dir / "semantic_review_reviewer_a_v0_3.json")
    reviewer_b = load(result_dir / "semantic_review_reviewer_b_v0_3.json")
    recorded_agreement = load(result_dir / "semantic_review_agreement_v0_3.json")
    assert reviewer_a["evidence_status"] == "completed_independent_review"
    assert reviewer_b["evidence_status"] == "completed_independent_review"
    assert recorded_agreement["evidence_status"] == (
        "independent_review_agreement_before_adjudication"
    )
    # JSON object keys are strings on disk; normalize the freshly recomputed
    # Boolean-label distributions through the same representation.
    recomputed_agreement = json.loads(
        json.dumps(analyze_semantic_review(reviewer_a, reviewer_b))
    )
    assert recorded_agreement == recomputed_agreement
    assert recorded_agreement["task_count"] == 30
    assert recorded_agreement["reviewer_a"] != recorded_agreement["reviewer_b"]

    reviewer_a_rows = {
        semantic_task_id(task): task["review"] for task in reviewer_a["tasks"]
    }
    reviewer_b_rows = {
        semantic_task_id(task): task["review"] for task in reviewer_b["tasks"]
    }
    adjudicated: dict[tuple[str, str], object] = {}
    if recorded_agreement["disagreement_count"]:
        adjudication_path = result_dir / "semantic_review_adjudication_v0_3.json"
        adjudication = load(adjudication_path)
        assert adjudication["evidence_status"] == (
            "completed_semantic_review_adjudication"
        )
        assert adjudication["agreement_sha256"] == digest(
            result_dir / "semantic_review_agreement_v0_3.json"
        )
        expected = {
            (item["task_id"], item["field"]): item
            for item in recorded_agreement["disagreements"]
        }
        records = {
            (item["task_id"], item["field"]): item
            for item in adjudication["records"]
        }
        assert adjudication["record_count"] == len(records) == len(expected)
        assert set(records) == set(expected)
        for key, item in records.items():
            original = expected[key]
            assert item["reviewer_a"] == original["reviewer_a"]
            assert item["reviewer_b"] == original["reviewer_b"]
            assert str(item["adjudicator"]).strip()
            assert str(item["date"]).strip()
            assert str(item["rationale"]).strip()
            adjudicated[key] = item["adjudicated_value"]

    # A completed review is not automatically a positive review. The release
    # gate accepts only a fully approved final interpretation; any retained
    # negative judgment requires revising the benchmark or its claims first.
    for identifier in reviewer_a_rows:
        for field in REVIEW_FIELDS:
            left_value = reviewer_a_rows[identifier][field]
            right_value = reviewer_b_rows[identifier][field]
            final_value = (
                left_value
                if left_value == right_value
                else adjudicated[(identifier, field)]
            )
            if field in BOOLEAN_FIELDS:
                assert final_value is True, f"unresolved negative review: {identifier} {field}"
            else:
                assert final_value == "approve", (
                    f"unresolved non-approval: {identifier} {field}"
                )

    frozen = load(result_dir / "novel_valid_audit_v0_1.json")
    reviewed = load(result_dir / "novel_valid_reviewed_v0_1.json")
    assert reviewed["evidence_status"] == "completed_human_outside_family_audit"
    assert reviewed["allowed_classifications"] == frozen["allowed_classifications"]
    frozen_cases = {case["audit_id"]: case for case in frozen["cases"]}
    reviewed_cases = {case["audit_id"]: case for case in reviewed["cases"]}
    assert len(frozen_cases) == 2 and set(reviewed_cases) == set(frozen_cases)
    reviewers = set()
    for identifier, case in reviewed_cases.items():
        original = frozen_cases[identifier]
        for field in ("source_path", "source_sha256", "plan"):
            assert case[field] == original[field]
        review = case["review"]
        assert isinstance(review["semantically_valid_at_declared_abstraction"], bool)
        assert isinstance(review["should_expand_constructed_family"], bool)
        assert review["classification"] in reviewed["allowed_classifications"]
        assert review["semantically_valid_at_declared_abstraction"] is True
        assert review["classification"] in {
            "valid_novel_or_nonminimal_plan",
            "constructed_family_coverage_miss",
        }
        if review["classification"] == "constructed_family_coverage_miss":
            assert review["should_expand_constructed_family"] is True
        assert review["reviewer"].strip() and review["date"].strip()
        reviewers.add(review["reviewer"].strip())
    assert len(reviewers) == 1


def verify(
    result_dir: Path,
    *,
    require_paper_data: bool,
    require_human_review: bool = False,
) -> None:
    config_path = ROOT / "configs" / "model_matrix_v0_2.json"
    verify_matrix(config_path, result_dir)
    config = load(config_path)
    queue = load(ROOT / config["queue"])
    expected_sources = {
        row["source_path"]: row["source_sha256"] for row in queue["records"]
    }
    models = {row["model_id"]: row for row in config["models"]}
    assert len(models) == 6
    common_prompt_hashes: dict[str, str] = {}

    for model in config["models"]:
        slug = model["slug"]
        raw_path = result_dir / f"{slug}_queue_100_sampling_v0_2.json"
        raw = load(raw_path)
        validate_raw_record(
            raw,
            model,
            config,
            expected_sources,
            common_prompt_hashes,
            path=raw_path,
        )
        assert raw["summary"]["completed_task_count"] == 100
        assert raw["summary"]["sample_count"] == 500

        enriched = load(result_dir / f"{slug}_queue_100_enriched_v0_2.json")
        assert enriched["model_id"] == model["model_id"]
        assert enriched["model_revision"] == model["revision"]
        assert len(enriched["tasks"]) == 100
        assert all(
            {"partial_order_match", "matched_reference_family_indices", "normalized_cost_regret"}
            <= sample.keys()
            for task in enriched["tasks"]
            for sample in task["samples"]
        )

        analysis = load(result_dir / f"{slug}_queue_100_analysis_v0_2.json")
        assert analysis["model_id"] == model["model_id"]
        assert analysis["model_revision"] == model["revision"]
        assert sum(analysis["failure_counts"].values()) == 500

    comparison = load(result_dir / "multi_model_comparison_v0_2.json")
    assert set(comparison["aggregate"]) == set(models)
    pairs = comparison["paired_comparisons"]
    expected_pairs = {frozenset(pair) for pair in itertools.combinations(models, 2)}
    actual_pairs = {
        frozenset((row["left_model"], row["right_model"])) for row in pairs
    }
    assert len(pairs) == 15 and actual_pairs == expected_pairs
    for row in pairs:
        assert set(row["metric_differences"]) == {"exact", "partial_order", "goal_valid"}
        for metric in row["metric_differences"].values():
            assert 0.0 <= metric["holm_adjusted_p_value"] <= 1.0

    for name in (
        "action_prefix_sensitivity_comparison_v0_2.json",
        "catalog_projection_sensitivity_comparison_v0_2_posthoc.json",
        "sampling_curve_analysis_v0_2.json",
    ):
        report = load(result_dir / name)
        assert {row["model_id"] for row in report["models"]} == set(models)

    if require_human_review:
        verify_human_review(result_dir)

    if require_paper_data:
        generated = ROOT / "paper" / "generated_v02.tex"
        assert generated.is_file()
        text = generated.read_text(encoding="utf-8")
        assert "Generated by paper/scripts/generate_v02_data.py" in text
        assert r"\newcommand{\VTwoModelCount}{6}" in text
        assert "TEMPORARY LAYOUT PLACEHOLDER" not in text

        human_generated = ROOT / "paper" / "generated_human_review.tex"
        assert human_generated.is_file()
        human_text = human_generated.read_text(encoding="utf-8")
        assert "Generated by paper/scripts/generate_human_review_data.py" in human_text
        if require_human_review:
            assert r"\newcommand{\HumanReviewEvidenceReady}{1}" in human_text

        manuscript = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
        table_layout = (ROOT / "paper" / "results_v02_tables.tex").read_text(
            encoding="utf-8"
        )
        assert r"\input{generated_v02.tex}" in manuscript
        assert r"\input{generated_human_review.tex}" in manuscript
        assert r"\input{results_v02_tables.tex}" in manuscript
        paper_sources = manuscript + "\n" + table_layout
        for macro in (
            r"\VTwoModelRows",
            r"\VTwoSensitivityRows",
            r"\VTwoQwenScaleRows",
            r"\VTwoSelectedPairRows",
            r"\VTwoDiversityRows",
            r"\VTwoAllPairRows",
        ):
            assert macro in paper_sources, f"paper does not consume {macro}"
        for stale in (
            "three-model results",
            "three compact open models",
            "1,500 primary outputs",
            r"\ConfirmatoryModelRows",
        ):
            assert stale not in manuscript, f"stale v0.1 manuscript text: {stale}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--require-paper-data", action="store_true")
    parser.add_argument("--require-human-review", action="store_true")
    args = parser.parse_args()
    verify(
        args.result_dir,
        require_paper_data=args.require_paper_data,
        require_human_review=args.require_human_review,
    )
    print("six-model v0.2 release verified")


if __name__ == "__main__":
    main()
