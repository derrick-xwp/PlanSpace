#!/usr/bin/env python3
"""Analyze a completed 100-task model run with task-level bootstrap intervals."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random


def sample_counts(tasks: list[dict[str, object]]) -> dict[str, float]:
    samples = [sample for task in tasks for sample in task["samples"]]
    total = len(samples)
    parsed = sum(sample["parse_error"] is None for sample in samples)
    executable = sum(
        bool(sample["execution"] and sample["execution"]["executable"])
        for sample in samples
    )
    valid = sum(
        bool(sample["execution"] and sample["execution"]["valid"])
        for sample in samples
    )
    exact = sum(bool(sample["exact_match"]) for sample in samples)
    partial_order = sum(bool(sample.get("partial_order_match")) for sample in samples)
    regrets = [
        sample["normalized_cost_regret"]
        for sample in samples
        if sample.get("normalized_cost_regret") is not None
    ]
    novel_valid = sum(
        bool(sample["execution"] and sample["execution"]["valid"])
        and not sample.get("partial_order_match", False)
        for sample in samples
    )
    unique_valid = sum(task["metrics"]["unique_valid_prediction_count"] for task in tasks)
    single_valid = sum(
        bool(task["samples"][0]["execution"] and task["samples"][0]["execution"]["valid"])
        for task in tasks
    )
    any_valid = sum(
        any(sample["execution"] and sample["execution"]["valid"] for sample in task["samples"])
        for task in tasks
    )
    any_exact = sum(
        any(sample["exact_match"] for sample in task["samples"]) for task in tasks
    )
    return {
        "task_count": len(tasks),
        "sample_count": total,
        "parse_success_rate": parsed / total,
        "executable_rate": executable / total,
        "goal_valid_rate": valid / total,
        "exact_match_rate": exact / total,
        "partial_order_match_rate": partial_order / total,
        "mean_normalized_cost_regret_among_valid": (
            sum(regrets) / len(regrets) if regrets else 0.0
        ),
        "novel_valid_rate_among_valid": novel_valid / valid if valid else 0.0,
        "valid_minus_exact": (valid - exact) / total,
        "single_reference_false_rejection_among_valid": (
            (valid - exact) / valid if valid else 0.0
        ),
        "unique_valid_predictions_per_task": unique_valid / len(tasks),
        "mean_reference_family_coverage": sum(
            task["metrics"].get("reference_family_coverage", 0.0) for task in tasks
        )
        / len(tasks),
        "valid_prediction_uniqueness": unique_valid / valid if valid else 0.0,
        "single_sample_goal_valid_rate": single_valid / len(tasks),
        "any_of_k_goal_valid_rate": any_valid / len(tasks),
        "any_of_k_exact_match_rate": any_exact / len(tasks),
    }


def percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def bootstrap(
    tasks: list[dict[str, object]], *, trials: int, seed: int
) -> dict[str, dict[str, float]]:
    rng = random.Random(seed)
    keys = (
        "parse_success_rate",
        "executable_rate",
        "goal_valid_rate",
        "exact_match_rate",
        "partial_order_match_rate",
        "mean_normalized_cost_regret_among_valid",
        "mean_reference_family_coverage",
        "novel_valid_rate_among_valid",
        "valid_minus_exact",
        "single_reference_false_rejection_among_valid",
    )
    draws = {key: [] for key in keys}
    for _ in range(trials):
        resampled = [tasks[rng.randrange(len(tasks))] for _ in tasks]
        metrics = sample_counts(resampled)
        for key in keys:
            draws[key].append(metrics[key])
    point = sample_counts(tasks)
    return {
        key: {
            "estimate": point[key],
            "ci95_low": percentile(draws[key], 0.025),
            "ci95_high": percentile(draws[key], 0.975),
        }
        for key in keys
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_results", type=Path)
    parser.add_argument("domain_audit", type=Path)
    parser.add_argument("--split-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--table-output", required=True, type=Path)
    parser.add_argument("--bootstrap-trials", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260914)
    args = parser.parse_args()

    model = json.loads(args.model_results.read_text(encoding="utf-8"))
    audit = json.loads(args.domain_audit.read_text(encoding="utf-8"))
    split_manifest = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    tasks = model["tasks"]
    expected_count = len(split_manifest["records"])
    samples_per_task = int(model["decoding"]["samples_per_task"])
    if len(tasks) != expected_count or any(
        len(task["samples"]) != samples_per_task for task in tasks
    ):
        raise ValueError(
            "analysis task/sample counts do not match the frozen split manifest and decoding"
        )
    audit_by_path = {record["source_path"]: record for record in audit["tasks"]}
    split_by_path = {
        record["source_path"]: record["split"] for record in split_manifest["records"]
    }
    if set(split_by_path) != {task["source_path"] for task in tasks}:
        raise ValueError("split manifest and model task paths differ")

    enriched = []
    failures = {
        "length_cap": 0,
        "parse": 0,
        "precondition": 0,
        "goal_miss": 0,
        "valid_exact": 0,
        "valid_nonexact": 0,
    }
    parse_error_types = Counter()
    for task in tasks:
        domain = audit_by_path[task["source_path"]]
        multiplicity = (
            domain["unique_plan_representative_count"] > 1
            or domain["topological_orders_checked"]
            > domain["unique_plan_representative_count"]
        )
        max_length = domain["plan_length_max"]
        length_bin = "1-3" if max_length <= 3 else "4-6" if max_length <= 6 else "7+"
        enriched.append(
            {
                **task,
                "operator_stratum": "+".join(domain["operator_vocabulary"]) or "NO_OP",
                "multiplicity_stratum": "multiple" if multiplicity else "single",
                "length_stratum": length_bin,
                "structural_split": split_by_path[task["source_path"]],
            }
        )
        for sample in task["samples"]:
            if sample["parse_error"] is not None:
                if sample["generated_tokens"] >= model["decoding"]["max_new_tokens"]:
                    failures["length_cap"] += 1
                    parse_error_types["length_cap"] += 1
                else:
                    failures["parse"] += 1
                    error = sample["parse_error"]
                    if "unknown action_id values" in error:
                        parse_error_types["unknown_action_id"] += 1
                    elif "does not contain a JSON object" in error:
                        parse_error_types["no_json_object"] += 1
                    elif "JSONDecodeError" in error:
                        parse_error_types["invalid_json"] += 1
                    elif "expected exactly one" in error or "plan item" in error:
                        parse_error_types["schema"] += 1
                    else:
                        parse_error_types["other"] += 1
            elif not sample["execution"]["executable"]:
                failures["precondition"] += 1
            elif not sample["execution"]["goal_satisfied"]:
                failures["goal_miss"] += 1
            elif sample["exact_match"]:
                failures["valid_exact"] += 1
            else:
                failures["valid_nonexact"] += 1

    strata = {}
    for label in (
        "structural_split",
        "operator_stratum",
        "multiplicity_stratum",
        "length_stratum",
    ):
        values = sorted({task[label] for task in enriched})
        strata[label] = {
            value: sample_counts([task for task in enriched if task[label] == value])
            for value in values
        }
    report = {
        "evidence_status": model["evidence_status"],
        "model_id": model["model_id"],
        "model_revision": model["model_revision"],
        "protocol_version": model["protocol_version"],
        "generic_domain_version": model["generic_domain_version"],
        "structural_split_version": split_manifest["split_version"],
        "bootstrap": {
            "unit": "task",
            "trials": args.bootstrap_trials,
            "seed": args.seed,
            "metrics": bootstrap(tasks, trials=args.bootstrap_trials, seed=args.seed),
        },
        "failure_counts": failures,
        "parse_error_types": dict(sorted(parse_error_types.items())),
        "strata": strata,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.table_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    ci = report["bootstrap"]["metrics"]
    lines = [
        f"# Frozen {len(tasks)}-task model analysis",
        "",
        f"Model: `{model['model_id']}` at `{model['model_revision']}`.",
        "",
        "| Metric | Estimate | 95% task-bootstrap CI |",
        "| --- | ---: | ---: |",
    ]
    for key in (
        "parse_success_rate",
        "executable_rate",
        "goal_valid_rate",
        "exact_match_rate",
        "partial_order_match_rate",
        "mean_normalized_cost_regret_among_valid",
        "mean_reference_family_coverage",
        "novel_valid_rate_among_valid",
        "valid_minus_exact",
        "single_reference_false_rejection_among_valid",
    ):
        item = ci[key]
        lines.append(
            f"| {key} | {item['estimate']:.2%} | "
            f"[{item['ci95_low']:.2%}, {item['ci95_high']:.2%}] |"
        )
    lines.extend(
        [
            "",
            "| Diversity metric | Value |",
            "| --- | ---: |",
            f"| First-sample goal validity | {sample_counts(tasks)['single_sample_goal_valid_rate']:.2%} |",
            f"| Any-of-{samples_per_task} goal validity | {sample_counts(tasks)['any_of_k_goal_valid_rate']:.2%} |",
            f"| Any-of-{samples_per_task} exact match | {sample_counts(tasks)['any_of_k_exact_match_rate']:.2%} |",
            f"| Unique valid plans per task | {sample_counts(tasks)['unique_valid_predictions_per_task']:.3f} |",
            f"| Unique fraction among valid samples | {sample_counts(tasks)['valid_prediction_uniqueness']:.2%} |",
            f"| Mean validated reference-family coverage | {sample_counts(tasks)['mean_reference_family_coverage']:.2%} |",
            f"| Novel valid outputs among valid | {sample_counts(tasks)['novel_valid_rate_among_valid']:.2%} |",
            f"| Mean normalized cost regret among valid | {sample_counts(tasks)['mean_normalized_cost_regret_among_valid']:.3f} |",
            "",
            "| Failure category | Count |",
            "| --- | ---: |",
            *[f"| {key} | {value} |" for key, value in failures.items()],
        ]
    )
    if parse_error_types:
        lines.extend(
            [
                "",
                "| Parse/format subtype | Count |",
                "| --- | ---: |",
                *[
                    f"| {key} | {value} |"
                    for key, value in sorted(parse_error_types.items())
                ],
            ]
        )
    for label, groups in strata.items():
        lines.extend(
            [
                "",
                f"## {label}",
                "",
                "| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for value, metrics in groups.items():
            lines.append(
                f"| {value} | {metrics['task_count']} | {metrics['sample_count']} | "
                f"{metrics['goal_valid_rate']:.2%} | {metrics['exact_match_rate']:.2%} | "
                f"{metrics['partial_order_match_rate']:.2%} | "
                f"{metrics['any_of_k_goal_valid_rate']:.2%} |"
            )
    args.table_output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
