#!/usr/bin/env python3
"""Add reference-DAG and partial-order metrics to a completed model run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import action_ids
from planspace.domain_registry import get_generic_domain
from planspace.partial_order import matches_partial_order


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_results", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--generic-domain-version",
        required=True,
        help="Frozen action-domain version declared by the raw artifact.",
    )
    args = parser.parse_args()
    domain = get_generic_domain(args.generic_domain_version)
    execute_plan = domain.execute_plan
    dependency_edges = domain.dependency_edges

    report = json.loads(args.model_results.read_text(encoding="utf-8"))
    tasks = report["tasks"]
    if not tasks or any(len(task["samples"]) != 5 for task in tasks):
        raise ValueError("enrichment requires a non-empty, completed five-sample matrix")
    if report.get("summary", {}).get("completed_task_count") != len(tasks):
        raise ValueError("enrichment input summary does not match its task records")

    total_matches = 0
    for task in tasks:
        source = parse_problem_file(args.source_root / task["source_path"])
        problem = domain.generic_household_problem(source)
        references_by_actions = {}
        for goal in problem.goal_alternatives:
            try:
                plan = domain.construct_goal_plan(problem, goal)
            except Exception:
                continue
            if not execute_plan(problem, plan).valid:
                continue
            ids = tuple(action_ids(plan))
            references_by_actions.setdefault(
                ids,
                {
                    "action_ids": list(ids),
                    "partial_order_edges": [
                        list(edge) for edge in sorted(dependency_edges(plan))
                    ],
                    "plan": plan,
                    "goals": [],
                },
            )["goals"].append(sorted(map(str, goal)))
        references = [
            references_by_actions[key] for key in sorted(references_by_actions)
        ]
        if not references:
            raise RuntimeError(f"no valid reference for {task['source_path']}")

        task_matches = 0
        matched_reference_indices = set()
        valid_regrets = []
        novel_valid_count = 0
        action_by_id = {action.action_id: action for action in problem.actions}
        minimum_reference_cost = min(
            sum(action.cost for action in reference["plan"])
            for reference in references
        )
        for sample in task["samples"]:
            matched_indices = []
            if sample["parse_error"] is None:
                matched_indices = [
                    index
                    for index, reference in enumerate(references)
                    if matches_partial_order(
                        sample["parsed_plan"],
                        reference["plan"],
                        frozenset(map(tuple, reference["partial_order_edges"])),
                    )
                ]
            matched = bool(matched_indices)
            sample["partial_order_match"] = matched
            sample["matched_reference_family_indices"] = matched_indices
            task_matches += int(matched)
            matched_reference_indices.update(matched_indices)
            is_valid = bool(sample["execution"] and sample["execution"]["valid"])
            if is_valid:
                candidate_cost = sum(
                    action_by_id[action_id].cost for action_id in sample["parsed_plan"]
                )
                regret = (
                    (candidate_cost - minimum_reference_cost) / minimum_reference_cost
                    if minimum_reference_cost
                    else 0.0
                )
                sample["normalized_cost_regret"] = regret
                valid_regrets.append(regret)
                novel_valid_count += int(not matched)
            else:
                sample["normalized_cost_regret"] = None
        total_matches += task_matches
        task["reference_plan_dags"] = [
            {
                "action_ids": reference["action_ids"],
                "partial_order_edges": reference["partial_order_edges"],
                "goals": reference["goals"],
            }
            for reference in references
        ]
        task["metrics"]["partial_order_match_rate"] = task_matches / len(
            task["samples"]
        )
        task["metrics"]["reference_family_coverage"] = (
            len(matched_reference_indices) / len(references)
        )
        task["metrics"]["matched_reference_family_count"] = len(
            matched_reference_indices
        )
        task["metrics"]["novel_valid_prediction_count"] = novel_valid_count
        task["metrics"]["mean_normalized_cost_regret"] = (
            sum(valid_regrets) / len(valid_regrets) if valid_regrets else None
        )

    report["summary"]["partial_order_match_rate"] = total_matches / sum(
        len(task["samples"]) for task in tasks
    )
    valid_samples = [
        sample
        for task in tasks
        for sample in task["samples"]
        if sample["execution"] and sample["execution"]["valid"]
    ]
    report["summary"]["mean_normalized_cost_regret_among_valid"] = (
        sum(sample["normalized_cost_regret"] for sample in valid_samples)
        / len(valid_samples)
        if valid_samples
        else None
    )
    report["summary"]["mean_reference_family_coverage"] = sum(
        task["metrics"]["reference_family_coverage"] for task in tasks
    ) / len(tasks)
    report["summary"]["novel_valid_rate_among_valid"] = (
        sum(not sample["partial_order_match"] for sample in valid_samples)
        / len(valid_samples)
        if valid_samples
        else None
    )
    report["partial_order_metric"] = {
        "generic_domain_version": args.generic_domain_version,
        "definition": "candidate realizes a topological ordering of any validated goal-plan representative DAG",
        "reference_count": sum(len(task["reference_plan_dags"]) for task in tasks),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
