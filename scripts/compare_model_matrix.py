#!/usr/bin/env python3
"""Create paired multi-model tables from completed enriched result matrices."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import random


METRICS = {
    "parse": lambda sample: sample["parse_error"] is None,
    "executable": lambda sample: bool(
        sample["execution"] and sample["execution"]["executable"]
    ),
    "goal_valid": lambda sample: bool(
        sample["execution"] and sample["execution"]["valid"]
    ),
    "exact": lambda sample: bool(sample["exact_match"]),
    "partial_order": lambda sample: bool(sample.get("partial_order_match")),
}


def task_metric(task: dict[str, object], metric: str) -> float:
    values = [METRICS[metric](sample) for sample in task["samples"]]
    return sum(values) / len(values)


def percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def paired_bootstrap(
    left: dict[str, dict[str, object]],
    right: dict[str, dict[str, object]],
    metric: str,
    *,
    trials: int,
    seed: int,
) -> dict[str, float]:
    paths = sorted(left)
    if paths != sorted(right):
        raise ValueError("paired models do not contain identical task paths")
    differences = [
        task_metric(left[path], metric) - task_metric(right[path], metric)
        for path in paths
    ]
    rng = random.Random(seed)
    draws = [
        sum(differences[rng.randrange(len(differences))] for _ in differences)
        / len(differences)
        for _ in range(trials)
    ]
    return {
        "estimate": sum(differences) / len(differences),
        "ci95_low": percentile(draws, 0.025),
        "ci95_high": percentile(draws, 0.975),
    }


def paired_sign_flip_test(
    left: dict[str, dict[str, object]],
    right: dict[str, dict[str, object]],
    metric: str,
    *,
    trials: int,
    seed: int,
) -> float:
    """Monte Carlo two-sided paired randomization test over task effects."""

    paths = sorted(left)
    if paths != sorted(right):
        raise ValueError("paired models do not contain identical task paths")
    differences = [
        task_metric(left[path], metric) - task_metric(right[path], metric)
        for path in paths
    ]
    observed = abs(sum(differences) / len(differences))
    rng = random.Random(seed)
    extreme = 0
    for _ in range(trials):
        permuted = abs(
            sum(value if rng.randrange(2) else -value for value in differences)
            / len(differences)
        )
        extreme += int(permuted >= observed - 1e-15)
    return (extreme + 1) / (trials + 1)


def holm_adjust(p_values: list[float]) -> list[float]:
    """Return Holm-adjusted p-values in the original order."""

    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [0.0] * len(p_values)
    running = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, (total - rank) * p_values[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def load_matrix(path: Path) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    tasks = report.get("tasks", [])
    samples_per_task = int(report.get("decoding", {}).get("samples_per_task", 0))
    if not tasks or samples_per_task <= 0 or any(
        len(task.get("samples", [])) != samples_per_task for task in tasks
    ):
        raise ValueError(f"incomplete matrix: {path}")
    if any("partial_order_match" not in sample for task in tasks for sample in task["samples"]):
        raise ValueError(f"matrix lacks partial-order enrichment: {path}")
    if any(
        "normalized_cost_regret" not in sample
        for task in tasks
        for sample in task["samples"]
    ) or any("reference_family_coverage" not in task["metrics"] for task in tasks):
        raise ValueError(f"matrix lacks cost or family enrichment: {path}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_results", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--table-output", required=True, type=Path)
    parser.add_argument("--bootstrap-trials", type=int, default=10000)
    parser.add_argument("--permutation-trials", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260914)
    args = parser.parse_args()
    if not args.model_results:
        raise ValueError("at least one model matrix is required")

    reports = [load_matrix(path) for path in args.model_results]
    versions = {
        (report["protocol_version"], report["generic_domain_version"])
        for report in reports
    }
    if len(versions) != 1:
        raise ValueError("model matrices use different frozen protocols")
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

    by_model = {
        report["model_id"]: {task["source_path"]: task for task in report["tasks"]}
        for report in reports
    }
    aggregate = {}
    for model_id, tasks_by_path in by_model.items():
        tasks = list(tasks_by_path.values())
        aggregate[model_id] = {
            metric: sum(task_metric(task, metric) for task in tasks) / len(tasks)
            for metric in METRICS
        }
        valid = sum(
            METRICS["goal_valid"](sample)
            for task in tasks
            for sample in task["samples"]
        )
        exact = sum(
            METRICS["exact"](sample)
            for task in tasks
            for sample in task["samples"]
        )
        aggregate[model_id]["false_rejection_among_valid"] = (
            (valid - exact) / valid if valid else 0.0
        )
        aggregate[model_id]["single_sample_goal_valid"] = sum(
            METRICS["goal_valid"](task["samples"][0]) for task in tasks
        ) / len(tasks)
        aggregate[model_id]["any_of_five_goal_valid"] = sum(
            any(METRICS["goal_valid"](sample) for sample in task["samples"])
            for task in tasks
        ) / len(tasks)
        aggregate[model_id]["mean_reference_family_coverage"] = sum(
            task["metrics"]["reference_family_coverage"] for task in tasks
        ) / len(tasks)
        regrets = [
            sample["normalized_cost_regret"]
            for task in tasks
            for sample in task["samples"]
            if sample["normalized_cost_regret"] is not None
        ]
        aggregate[model_id]["mean_normalized_cost_regret_among_valid"] = (
            sum(regrets) / len(regrets) if regrets else 0.0
        )

    comparisons = []
    for pair_index, (left_id, right_id) in enumerate(itertools.combinations(by_model, 2)):
        metric_differences = {
            metric: {
                **paired_bootstrap(
                    by_model[left_id],
                    by_model[right_id],
                    metric,
                    trials=args.bootstrap_trials,
                    seed=args.seed + pair_index * 100 + metric_index,
                ),
                "paired_sign_flip_p_value": paired_sign_flip_test(
                    by_model[left_id],
                    by_model[right_id],
                    metric,
                    trials=args.permutation_trials,
                    seed=args.seed + 100_000 + pair_index * 100 + metric_index,
                ),
            }
            for metric_index, metric in enumerate(
                ("exact", "partial_order", "goal_valid")
            )
        }
        comparisons.append(
            {
                "left_model": left_id,
                "right_model": right_id,
                "metric_differences": metric_differences,
            }
        )

    for metric in ("exact", "partial_order", "goal_valid"):
        adjusted = holm_adjust(
            [
                item["metric_differences"][metric]["paired_sign_flip_p_value"]
                for item in comparisons
            ]
        )
        for item, value in zip(comparisons, adjusted):
            result = item["metric_differences"][metric]
            result["holm_adjusted_p_value"] = value
            result["holm_reject_0_05"] = value < 0.05

    rankings = {
        metric: sorted(
            aggregate,
            key=lambda model_id: (-aggregate[model_id][metric], model_id),
        )
        for metric in ("exact", "partial_order", "goal_valid")
    }
    report = {
        "protocol_version": reports[0]["protocol_version"],
        "generic_domain_version": reports[0]["generic_domain_version"],
        "bootstrap": {
            "unit": "paired task",
            "trials": args.bootstrap_trials,
            "seed": args.seed,
        },
        "paired_randomization": {
            "unit": "paired task",
            "trials": args.permutation_trials,
            "seed_offset": 100000,
            "multiplicity": "Holm correction across all model pairs within each metric",
        },
        "aggregate": aggregate,
        "rankings": rankings,
        "paired_comparisons": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.table_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# {len(reports)}-model paired comparison",
        "",
        f"All values use the same {task_count} tasks and {samples_per_task} samples per task.",
        "",
        "| Model | Parse | Executable | Goal valid | Exact | Partial order | False rejection among valid |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model_id, metrics in aggregate.items():
        lines.append(
            f"| {model_id} | {metrics['parse']:.2%} | {metrics['executable']:.2%} | "
            f"{metrics['goal_valid']:.2%} | {metrics['exact']:.2%} | "
            f"{metrics['partial_order']:.2%} | "
            f"{metrics['false_rejection_among_valid']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## Sampling diversity and cost",
            "",
            "| Model | First-sample goal | Any-of-five goal | Family coverage | Mean cost regret |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for model_id, metrics in aggregate.items():
        lines.append(
            f"| {model_id} | {metrics['single_sample_goal_valid']:.2%} | "
            f"{metrics['any_of_five_goal_valid']:.2%} | "
            f"{metrics['mean_reference_family_coverage']:.2%} | "
            f"{metrics['mean_normalized_cost_regret_among_valid']:.3f} |"
        )
    lines.extend(["", "## Paired task-bootstrap differences", ""])
    for comparison in comparisons:
        lines.extend(
            [
                f"### {comparison['left_model']} minus {comparison['right_model']}",
                "",
                "| Metric | Difference | 95% CI | Holm p |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for metric, item in comparison["metric_differences"].items():
            lines.append(
                f"| {metric} | {item['estimate']:+.2%} | "
                f"[{item['ci95_low']:+.2%}, {item['ci95_high']:+.2%}] | "
                f"{item['holm_adjusted_p_value']:.4f} |"
            )
        lines.append("")
    lines.extend(["## Rankings", ""])
    for metric, order in rankings.items():
        lines.append(f"- {metric}: " + " > ".join(order))
    args.table_output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
