#!/usr/bin/env python3
"""Measure a post-hoc exact catalog-record projection sensitivity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random

from planspace.bddl_parser import parse_problem_file
from planspace.domain_registry import get_generic_domain
from planspace.model_protocol import parse_model_plan_catalog_projection_sensitivity


def percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def aggregate(tasks: list[dict[str, object]]) -> dict[str, float | int]:
    samples = [sample for task in tasks for sample in task["samples"]]
    total = len(samples)
    fields = (
        "strict_parse_success",
        "projected_parse_success",
        "strict_goal_valid",
        "projected_goal_valid",
        "strict_exact_match",
        "projected_exact_match",
    )
    rates = {field: sum(bool(row[field]) for row in samples) / total for field in fields}
    return {
        "sample_count": total,
        "strict_parse_rate": rates["strict_parse_success"],
        "projected_parse_rate": rates["projected_parse_success"],
        "parse_rate_delta": rates["projected_parse_success"] - rates["strict_parse_success"],
        "strict_goal_valid_rate": rates["strict_goal_valid"],
        "projected_goal_valid_rate": rates["projected_goal_valid"],
        "goal_valid_rate_delta": rates["projected_goal_valid"] - rates["strict_goal_valid"],
        "strict_exact_match_rate": rates["strict_exact_match"],
        "projected_exact_match_rate": rates["projected_exact_match"],
        "exact_match_rate_delta": rates["projected_exact_match"] - rates["strict_exact_match"],
        "newly_recovered_valid_count": sum(
            not row["strict_goal_valid"] and row["projected_goal_valid"] for row in samples
        ),
    }


def bootstrap_deltas(
    tasks: list[dict[str, object]], *, trials: int, seed: int
) -> dict[str, dict[str, float]]:
    keys = ("parse_rate_delta", "goal_valid_rate_delta", "exact_match_rate_delta")
    draws = {key: [] for key in keys}
    rng = random.Random(seed)
    for _ in range(trials):
        resample = [tasks[rng.randrange(len(tasks))] for _ in tasks]
        metrics = aggregate(resample)
        for key in keys:
            draws[key].append(metrics[key])
    point = aggregate(tasks)
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
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generic-domain-version", required=True)
    parser.add_argument("--bootstrap-trials", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260915)
    args = parser.parse_args()
    domain = get_generic_domain(args.generic_domain_version)
    execute_plan = domain.execute_plan

    report = json.loads(args.model_results.read_text(encoding="utf-8"))
    tasks = report.get("tasks", [])
    if not tasks or any(len(task.get("samples", [])) != 5 for task in tasks):
        raise ValueError("sensitivity requires a non-empty, completed five-sample matrix")
    if report.get("summary", {}).get("completed_task_count") != len(tasks):
        raise ValueError("sensitivity input summary does not match its task records")

    task_rows = []
    for task in tasks:
        source = parse_problem_file(args.source_root / task["source_path"])
        problem = domain.generic_household_problem(source)
        action_by_id = {action.action_id: action for action in problem.actions}
        projected_samples = []
        for sample in task["samples"]:
            try:
                plan = parse_model_plan_catalog_projection_sensitivity(
                    sample["raw_output"], problem.actions
                )
                execution = execute_plan(problem, [action_by_id[item] for item in plan])
                error = None
                execution_row = {
                    "executable": execution.executable,
                    "goal_satisfied": execution.goal_satisfied,
                    "valid": execution.valid,
                    "failure_step": execution.failure_step,
                    "failed_action_id": execution.failed_action_id,
                    "missing_preconditions": sorted(map(str, execution.missing_preconditions)),
                }
            except Exception as exc:
                plan = tuple()
                execution_row = None
                error = f"{type(exc).__name__}: {exc}"
            projected_samples.append(
                {
                    "sample_index": sample["sample_index"],
                    "strict_parse_success": sample["parse_error"] is None,
                    "strict_goal_valid": bool(sample["execution"] and sample["execution"]["valid"]),
                    "strict_exact_match": bool(sample["exact_match"]),
                    "projected_plan": list(plan),
                    "projected_parse_success": error is None,
                    "projected_parse_error": error,
                    "projected_execution": execution_row,
                    "projected_goal_valid": bool(execution_row and execution_row["valid"]),
                    "projected_exact_match": tuple(plan) == tuple(task["reference_plan"])
                    if error is None
                    else False,
                }
            )
        task_rows.append({"source_path": task["source_path"], "samples": projected_samples})

    output = {
        "evidence_status": "posthoc_exploratory_interface_sensitivity",
        "analysis_version": "planspace-exact-catalog-projection-sensitivity-v0.1",
        "model_id": report["model_id"],
        "model_revision": report["model_revision"],
        "protocol_version": report["protocol_version"],
        "generic_domain_version": args.generic_domain_version,
        "normalization_rule": (
            "accept an exact allowed action id, its literal action_id= form, or an exact "
            "catalog record rendered in the prompt; no splitting, fuzzy matching, or JSON repair"
        ),
        "summary": aggregate(task_rows),
        "bootstrap": {
            "unit": "task",
            "trials": args.bootstrap_trials,
            "seed": args.seed,
            "deltas": bootstrap_deltas(task_rows, trials=args.bootstrap_trials, seed=args.seed),
        },
        "tasks": task_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], indent=2))


if __name__ == "__main__":
    main()
