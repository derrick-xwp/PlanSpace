#!/usr/bin/env python3
"""Paired task analysis of two prompt-serialization conditions per model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random

from scripts.compare_model_matrix import holm_adjust, percentile


METRICS = {
    "parse": lambda sample: sample["parse_error"] is None,
    "executable": lambda sample: bool(sample["execution"] and sample["execution"]["executable"]),
    "goal_valid": lambda sample: bool(sample["execution"] and sample["execution"]["valid"]),
    "partial_order": lambda sample: bool(sample.get("partial_order_match")),
    "exact": lambda sample: bool(sample["exact_match"]),
}


def task_rate(task: dict, metric: str) -> float:
    values = [METRICS[metric](sample) for sample in task["samples"]]
    return sum(values) / len(values)


def paired_effect(
    old_tasks: dict[str, dict],
    new_tasks: dict[str, dict],
    metric: str,
    *,
    trials: int,
    seed: int,
) -> dict:
    paths = sorted(old_tasks)
    if paths != sorted(new_tasks):
        raise ValueError("conditions contain different task paths")
    differences = [
        task_rate(new_tasks[path], metric) - task_rate(old_tasks[path], metric)
        for path in paths
    ]
    rng = random.Random(seed)
    draws = [
        sum(differences[rng.randrange(len(differences))] for _ in differences)
        / len(differences)
        for _ in range(trials)
    ]
    observed = abs(sum(differences) / len(differences))
    rng = random.Random(seed + 1_000_000)
    extreme = 0
    for _ in range(trials):
        value = abs(
            sum(delta if rng.randrange(2) else -delta for delta in differences)
            / len(differences)
        )
        extreme += int(value >= observed - 1e-15)
    return {
        "old_rate": sum(task_rate(old_tasks[path], metric) for path in paths) / len(paths),
        "new_rate": sum(task_rate(new_tasks[path], metric) for path in paths) / len(paths),
        "estimate": sum(differences) / len(differences),
        "ci95_low": percentile(draws, 0.025),
        "ci95_high": percentile(draws, 0.975),
        "paired_sign_flip_p_value": (extreme + 1) / (trials + 1),
    }


def load_condition(config_path: Path, result_dir: Path) -> tuple[dict, dict[str, dict]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    suffix = config["artifact_suffix"]
    task_count = int(config.get("task_count", 100))
    reports = {}
    for model in config["models"]:
        path = result_dir / f"{model['slug']}_queue_{task_count}_enriched_{suffix}.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["model_id"] != model["model_id"] or report["model_revision"] != model["revision"]:
            raise ValueError(f"model identity mismatch: {path}")
        if len(report["tasks"]) != task_count:
            raise ValueError(f"incomplete condition: {path}")
        reports[model["model_id"]] = report
    return config, reports


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("old_config", type=Path)
    parser.add_argument("old_result_dir", type=Path)
    parser.add_argument("new_config", type=Path)
    parser.add_argument("new_result_dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--table-output", required=True, type=Path)
    parser.add_argument("--trials", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260916)
    args = parser.parse_args()

    old_config, old_reports = load_condition(args.old_config, args.old_result_dir)
    new_config, new_reports = load_condition(args.new_config, args.new_result_dir)
    if set(old_reports) != set(new_reports):
        raise ValueError("conditions contain different model identities")
    if old_config["generic_domain_version"] != new_config["generic_domain_version"]:
        raise ValueError("conditions use different action-domain versions")
    if old_config["decoding"] != new_config["decoding"]:
        raise ValueError("conditions use different decoding schedules")

    models = []
    for model_index, model_id in enumerate(old_reports):
        old = old_reports[model_id]
        new = new_reports[model_id]
        if old["model_revision"] != new["model_revision"]:
            raise ValueError(f"model revision mismatch for {model_id}")
        if old["decoding"] != new["decoding"] or old["decoding"] != old_config["decoding"]:
            raise ValueError(f"recorded decoding mismatch for {model_id}")
        old_tasks = {task["source_path"]: task for task in old["tasks"]}
        new_tasks = {task["source_path"]: task for task in new["tasks"]}
        if {
            task["source_path"]: task["source_sha256"] for task in old["tasks"]
        } != {
            task["source_path"]: task["source_sha256"] for task in new["tasks"]
        }:
            raise ValueError(f"source hash mismatch for {model_id}")
        for source_path in old_tasks:
            old_schedule = [
                (sample["sample_index"], sample["seed"])
                for sample in old_tasks[source_path]["samples"]
            ]
            new_schedule = [
                (sample["sample_index"], sample["seed"])
                for sample in new_tasks[source_path]["samples"]
            ]
            if old_schedule != new_schedule:
                raise ValueError(f"sample schedule mismatch for {model_id}: {source_path}")
        prompt_hash_changed_task_count = sum(
            old_tasks[path]["prompt_sha256"] != new_tasks[path]["prompt_sha256"]
            for path in old_tasks
        )
        serialized_chat_hash_changed_task_count = sum(
            old_tasks[path]["serialized_chat_sha256"]
            != new_tasks[path]["serialized_chat_sha256"]
            for path in old_tasks
        )
        effects = {
            metric: paired_effect(
                old_tasks,
                new_tasks,
                metric,
                trials=args.trials,
                seed=args.seed + model_index * 100 + metric_index,
            )
            for metric_index, metric in enumerate(METRICS)
        }
        models.append(
            {
                "model_id": model_id,
                "model_revision": old["model_revision"],
                "task_count": len(old_tasks),
                "prompt_hash_changed_task_count": prompt_hash_changed_task_count,
                "serialized_chat_hash_changed_task_count": serialized_chat_hash_changed_task_count,
                "effects": effects,
            }
        )

    for metric in METRICS:
        adjusted = holm_adjust(
            [row["effects"][metric]["paired_sign_flip_p_value"] for row in models]
        )
        for row, value in zip(models, adjusted):
            row["effects"][metric]["holm_adjusted_p_value"] = value
            row["effects"][metric]["holm_reject_0_05"] = value < 0.05

    report = {
        "evidence_status": "controlled_same_seed_same_domain_prompt_serialization_comparison",
        "analysis_version": "planspace-prompt-serialization-effect-v0.1",
        "old_protocol_version": old_config["protocol_version"],
        "new_protocol_version": new_config["protocol_version"],
        "generic_domain_version": new_config["generic_domain_version"],
        "decoding": new_config["decoding"],
        "bootstrap": {"unit": "paired task", "trials": args.trials, "seed": args.seed},
        "models": models,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.table_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Controlled prompt-serialization effect",
        "",
        "New minus old percentage-point effects; intervals use paired task bootstrap and p-values use paired sign-flip tests with Holm correction across six models per metric.",
        "",
        "| Model | Parse | Executable | Goal valid | Partial order | Exact |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in models:
        values = []
        for metric in METRICS:
            effect = row["effects"][metric]
            values.append(
                f"{100 * effect['estimate']:+.1f} [{100 * effect['ci95_low']:+.1f}, {100 * effect['ci95_high']:+.1f}]"
            )
        lines.append(f"| {row['model_id']} | " + " | ".join(values) + " |")
    args.table_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"compared {len(models)} models")


if __name__ == "__main__":
    main()
