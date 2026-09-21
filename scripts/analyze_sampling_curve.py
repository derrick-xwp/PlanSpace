#!/usr/bin/env python3
"""Measure task success and plan-family coverage as the sample budget grows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random


METRIC_NAMES = (
    "any_goal_valid_rate",
    "mean_reference_family_coverage",
    "mean_unique_valid_plans",
)


def percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def task_prefix_metrics(task: dict[str, object], k: int) -> dict[str, float]:
    samples = sorted(task["samples"], key=lambda sample: sample["sample_index"])
    if [sample["sample_index"] for sample in samples] != list(range(len(samples))):
        raise ValueError("sample indices must be consecutive and zero based")
    if not 1 <= k <= len(samples):
        raise ValueError(f"invalid prefix length {k} for {len(samples)} samples")
    prefix = samples[:k]
    valid_plans = {
        tuple(sample["parsed_plan"])
        for sample in prefix
        if sample["execution"] and sample["execution"]["valid"]
    }
    matched_families = {
        family_index
        for sample in prefix
        for family_index in sample["matched_reference_family_indices"]
    }
    family_count = len(task["reference_plan_dags"])
    if family_count == 0:
        raise ValueError("every task must have at least one reference family")
    return {
        "any_goal_valid_rate": float(bool(valid_plans)),
        "mean_reference_family_coverage": len(matched_families) / family_count,
        "mean_unique_valid_plans": float(len(valid_plans)),
    }


def aggregate_prefix(tasks: list[dict[str, object]], k: int) -> dict[str, float]:
    per_task = [task_prefix_metrics(task, k) for task in tasks]
    return {
        metric: sum(item[metric] for item in per_task) / len(per_task)
        for metric in METRIC_NAMES
    }


def bootstrap_prefix(
    tasks: list[dict[str, object]],
    k: int,
    *,
    trials: int,
    seed: int,
) -> dict[str, dict[str, float]]:
    per_task = [task_prefix_metrics(task, k) for task in tasks]
    point = {
        metric: sum(item[metric] for item in per_task) / len(per_task)
        for metric in METRIC_NAMES
    }
    rng = random.Random(seed)
    draws = {metric: [] for metric in METRIC_NAMES}
    for _ in range(trials):
        indices = [rng.randrange(len(per_task)) for _ in per_task]
        for metric in METRIC_NAMES:
            draws[metric].append(
                sum(per_task[index][metric] for index in indices) / len(indices)
            )
    return {
        metric: {
            "estimate": point[metric],
            "ci95_low": percentile(draws[metric], 0.025),
            "ci95_high": percentile(draws[metric], 0.975),
        }
        for metric in METRIC_NAMES
    }


def load_matrix(path: Path) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    tasks = report.get("tasks", [])
    samples_per_task = int(report.get("decoding", {}).get("samples_per_task", 0))
    if not tasks or samples_per_task <= 0 or any(
        len(task.get("samples", [])) != samples_per_task for task in tasks
    ):
        raise ValueError(f"incomplete sampled matrix: {path}")
    for task in tasks:
        if not task.get("reference_plan_dags"):
            raise ValueError(f"missing reference families in {path}")
        if any(
            "matched_reference_family_indices" not in sample
            for sample in task["samples"]
        ):
            raise ValueError(f"matrix lacks partial-order enrichment: {path}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_results", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--table-output", required=True, type=Path)
    parser.add_argument("--bootstrap-trials", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260914)
    args = parser.parse_args()

    reports = [load_matrix(path) for path in args.model_results]
    task_counts = {len(report["tasks"]) for report in reports}
    sample_counts = {
        int(report["decoding"]["samples_per_task"]) for report in reports
    }
    source_sets = {
        tuple(sorted(task["source_path"] for task in report["tasks"]))
        for report in reports
    }
    if len(task_counts) != 1 or len(sample_counts) != 1 or len(source_sets) != 1:
        raise ValueError("model matrices use different task or sample sets")
    task_count = next(iter(task_counts))
    samples_per_task = next(iter(sample_counts))
    models = []
    for model_index, report in enumerate(reports):
        points = []
        for k in range(1, samples_per_task + 1):
            points.append(
                {
                    "k": k,
                    "metrics": bootstrap_prefix(
                        report["tasks"],
                        k,
                        trials=args.bootstrap_trials,
                        seed=args.seed + model_index * 100 + k,
                    ),
                }
            )
        models.append(
            {
                "model_id": report["model_id"],
                "model_revision": report["model_revision"],
                "task_count": len(report["tasks"]),
                "samples_per_task": samples_per_task,
                "points": points,
            }
        )

    output = {
        "evidence_status": "complete_frozen_outputs_pending_semantic_review",
        "analysis_version": "planspace-sampling-curve-v0.1",
        "sample_order": "ascending sample_index over the frozen seeds",
        "bootstrap": {
            "unit": "task",
            "trials": args.bootstrap_trials,
            "seed": args.seed,
        },
        "models": models,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.table_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Sampling-budget curves",
        "",
        f"All estimates average over the same {task_count} tasks. Prefixes follow ascending "
        f"sample index over the {samples_per_task} frozen seeds.",
        "",
        "| Model | k | Any goal valid | Mean family coverage | Mean unique valid plans |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for model in models:
        for point in model["points"]:
            metrics = point["metrics"]
            lines.append(
                f"| {model['model_id']} | {point['k']} | "
                f"{metrics['any_goal_valid_rate']['estimate']:.2%} | "
                f"{metrics['mean_reference_family_coverage']['estimate']:.2%} | "
                f"{metrics['mean_unique_valid_plans']['estimate']:.3f} |"
            )
    args.table_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
