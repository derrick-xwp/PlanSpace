#!/usr/bin/env python3
"""Report full-denominator and executable-conditional cost-bounded validity."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def bootstrap_interval(task_values: list[float], *, trials: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    count = len(task_values)
    estimates = [
        sum(task_values[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(trials)
    ]
    return [quantile(estimates, 0.025), quantile(estimates, 0.975)]


def analyze(path: Path, thresholds: list[float], *, trials: int, seed: int) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    total = sum(len(task["samples"]) for task in data["tasks"])
    executable = sum(
        bool((sample.get("execution") or {}).get("executable"))
        for task in data["tasks"]
        for sample in task["samples"]
    )
    goal_valid = sum(
        bool((sample.get("execution") or {}).get("valid"))
        for task in data["tasks"]
        for sample in task["samples"]
    )
    for threshold_index, threshold in enumerate(thresholds):
        accepted = 0
        per_task = []
        for task in data["tasks"]:
            task_accepted = 0
            for sample in task["samples"]:
                valid = bool((sample.get("execution") or {}).get("valid"))
                regret = sample.get("normalized_cost_regret")
                bounded = valid and regret is not None and regret <= threshold + 1e-12
                accepted += int(bounded)
                task_accepted += int(bounded)
            per_task.append(task_accepted / len(task["samples"]))
        interval = bootstrap_interval(per_task, trials=trials, seed=seed + threshold_index)
        rows.append(
            {
                "normalized_cost_regret_threshold": threshold,
                "accepted_count": accepted,
                "full_denominator_rate": accepted / total,
                "full_denominator_task_bootstrap_95ci": interval,
                "executable_conditional_rate": accepted / executable if executable else None,
                "goal_valid_retention_rate": accepted / goal_valid if goal_valid else None,
            }
        )
    return {
        "model_id": data["model_id"],
        "model_revision": data.get("model_revision"),
        "artifact": str(path),
        "artifact_sha256": sha256(path),
        "task_count": len(data["tasks"]),
        "output_count": total,
        "executable_count": executable,
        "goal_valid_count": goal_valid,
        "thresholds": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--thresholds", nargs="+", type=float, default=[0.0, 0.25, 0.5, 1.0])
    parser.add_argument("--bootstrap-trials", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260918)
    args = parser.parse_args()

    models = [
        analyze(path, args.thresholds, trials=args.bootstrap_trials, seed=args.seed + index * 100)
        for index, path in enumerate(args.artifacts)
    ]
    if {model["task_count"] for model in models} != {171}:
        raise ValueError("cost-bounded primary analysis requires 171 tasks per model")
    if sum(model["output_count"] for model in models) != 5130:
        raise ValueError("cost-bounded primary analysis requires 5,130 outputs")
    report = {
        "evidence_status": "post_hoc_cost_threshold_sensitivity",
        "analysis_version": "planspace-cost-bounded-goal-validity-v0.1",
        "definition": (
            "A plan is accepted at threshold tau iff replay reaches the goal and "
            "(plan_cost - minimum_reference_cost) / minimum_reference_cost <= tau."
        ),
        "denominator_policy": (
            "The primary rate uses all outputs. Executable-conditional rates are diagnostic; "
            "goal-valid retention isolates the effect of the cost bound."
        ),
        "bootstrap": {"unit": "task", "trials": args.bootstrap_trials, "seed": args.seed},
        "thresholds": args.thresholds,
        "models": models,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output:
        lines = [
            "# Cost-bounded goal validity",
            "",
            report["definition"],
            "",
            "| Model | Goal-valid | tau=0 | tau=0.25 | tau=0.5 | tau=1.0 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for model in models:
            rates = {row["normalized_cost_regret_threshold"]: row["full_denominator_rate"] for row in model["thresholds"]}
            lines.append(
                f"| {model['model_id']} | {100 * model['goal_valid_count'] / model['output_count']:.1f} | "
                + " | ".join(f"{100 * rates[t]:.1f}" for t in args.thresholds)
                + " |"
            )
        args.markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"models": len(models), "outputs": sum(m["output_count"] for m in models)}, indent=2))


if __name__ == "__main__":
    main()
