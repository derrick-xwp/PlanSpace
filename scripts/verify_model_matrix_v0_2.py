#!/usr/bin/env python3
"""Fail closed unless the configured six-model matrix bundle is complete."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path


def load(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_matrix(config_path: Path, result_dir: Path) -> None:
    config = load(config_path)
    artifact_suffix = config.get("artifact_suffix", "v0_2")
    task_count = int(config.get("task_count", 100))
    samples_per_task = int(config["decoding"]["samples_per_task"])
    sample_count = task_count * samples_per_task
    model_ids = {model["model_id"] for model in config["models"]}
    if len(model_ids) != 6:
        raise AssertionError("matrix protocol must declare exactly six distinct models")

    expected_decoding = {
        "samples_per_task": config["decoding"]["samples_per_task"],
        "seed_base": config["decoding"]["seed_base"],
        "temperature": config["decoding"]["temperature"],
        "top_p": config["decoding"]["top_p"],
        "max_new_tokens": config["decoding"]["max_new_tokens"],
        "enable_thinking": config["decoding"]["enable_thinking"],
    }
    for model in config["models"]:
        slug = model["slug"]
        raw = load(result_dir / f"{slug}_queue_{task_count}_sampling_{artifact_suffix}.json")
        assert raw["model_id"] == model["model_id"]
        assert raw["model_revision"] == model["revision"]
        assert raw["protocol_version"] == config["protocol_version"]
        if config.get("evidence_status"):
            assert raw["evidence_status"] == config["evidence_status"]
        assert raw["decoding"] == expected_decoding
        assert raw["summary"]["completed_task_count"] == task_count
        assert raw["summary"]["sample_count"] == sample_count
        assert len(raw["tasks"]) == task_count
        assert all(len(task["samples"]) == samples_per_task for task in raw["tasks"])
        assert all(len(task["serialized_chat_sha256"]) == 64 for task in raw["tasks"])

        enriched = load(result_dir / f"{slug}_queue_{task_count}_enriched_{artifact_suffix}.json")
        assert enriched["model_id"] == model["model_id"]
        assert len(enriched["tasks"]) == task_count
        assert all(
            {"partial_order_match", "matched_reference_family_indices", "normalized_cost_regret"}
            <= sample.keys()
            for task in enriched["tasks"]
            for sample in task["samples"]
        )
        assert all("reference_family_coverage" in task["metrics"] for task in enriched["tasks"])

        analysis = load(result_dir / f"{slug}_queue_{task_count}_analysis_{artifact_suffix}.json")
        assert analysis["model_id"] == model["model_id"]
        assert analysis["bootstrap"]["trials"] == 10_000
        assert sum(analysis["failure_counts"].values()) == sample_count
        assert sum(
            row["task_count"] for row in analysis["strata"]["structural_split"].values()
        ) == task_count

        prefix = load(result_dir / f"{slug}_action_prefix_sensitivity_{artifact_suffix}.json")
        assert prefix["model_id"] == model["model_id"]
        assert prefix["summary"]["sample_count"] == sample_count
        assert prefix["bootstrap"]["trials"] == 10_000

        projection = load(
            result_dir / f"{slug}_catalog_projection_sensitivity_{artifact_suffix}_posthoc.json"
        )
        assert projection["model_id"] == model["model_id"]
        assert projection["evidence_status"] == "posthoc_exploratory_interface_sensitivity"
        assert projection["summary"]["sample_count"] == sample_count
        assert projection["bootstrap"]["trials"] == 10_000

    comparison = load(result_dir / f"multi_model_comparison_{artifact_suffix}.json")
    assert set(comparison["aggregate"]) == model_ids
    assert len(comparison["paired_comparisons"]) == len(list(itertools.combinations(model_ids, 2)))
    for pair in comparison["paired_comparisons"]:
        assert {pair["left_model"], pair["right_model"]} <= model_ids
        for metric in ("exact", "partial_order", "goal_valid"):
            values = pair["metric_differences"][metric]
            assert {
                "estimate",
                "ci95_low",
                "ci95_high",
                "paired_sign_flip_p_value",
                "holm_adjusted_p_value",
                "holm_reject_0_05",
            } <= values.keys()

    sampling = load(result_dir / f"sampling_curve_analysis_{artifact_suffix}.json")
    assert sampling["bootstrap"]["trials"] == 10_000
    assert {row["model_id"] for row in sampling["models"]} == model_ids
    assert all(row["task_count"] == task_count for row in sampling["models"])
    assert all(row["samples_per_task"] == samples_per_task for row in sampling["models"])
    assert all(
        [point["k"] for point in row["points"]] == list(range(1, samples_per_task + 1))
        for row in sampling["models"]
    )

    prefix_summary = load(result_dir / f"action_prefix_sensitivity_comparison_{artifact_suffix}.json")
    assert {row["model_id"] for row in prefix_summary["models"]} == model_ids
    projection_summary = load(
        result_dir / f"catalog_projection_sensitivity_comparison_{artifact_suffix}_posthoc.json"
    )
    assert projection_summary["evidence_status"] == "posthoc_exploratory_interface_sensitivity"
    assert {row["model_id"] for row in projection_summary["models"]} == model_ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()
    verify_matrix(args.config, args.result_dir)
    print(f"six-model {json.loads(args.config.read_text(encoding='utf-8')).get('artifact_suffix', 'v0_2')} matrix verified")


if __name__ == "__main__":
    main()
