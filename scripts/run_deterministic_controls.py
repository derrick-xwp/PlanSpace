#!/usr/bin/env python3
"""Run 100-task positive-alternative and deletion-negative controls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import action_ids, execute_plan
from planspace.generic_domain import construct_goal_plan, generic_household_problem
from planspace.partial_order import (
    dependency_edges,
    matches_partial_order,
    topological_orders,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--table-output", required=True, type=Path)
    parser.add_argument(
        "--evidence-status",
        default="candidate_controls_pending_semantic_review",
    )
    parser.add_argument(
        "--control-version", default="planspace-deterministic-controls-v0.1"
    )
    parser.add_argument(
        "--table-boundary",
        default="Candidate action semantics pending independent review.",
    )
    args = parser.parse_args()

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    tasks = []
    for queued in queue["records"]:
        source = parse_problem_file(args.source_root / queued["source_path"])
        problem = generic_household_problem(source)
        refs_by_ids = {}
        for goal in problem.goal_alternatives:
            try:
                plan = construct_goal_plan(problem, goal)
            except Exception:
                continue
            if execute_plan(problem, plan).valid:
                refs_by_ids.setdefault(action_ids(plan), plan)
        references = [refs_by_ids[key] for key in sorted(refs_by_ids)]
        if not references:
            raise RuntimeError(f"no reference for {queued['source_path']}")
        primary = references[0]

        alternative = None
        alternative_kind = None
        for candidate in references[1:]:
            if action_ids(candidate) != action_ids(primary):
                alternative = candidate
                alternative_kind = "goal_binding"
                break
        if alternative is None:
            edges = dependency_edges(primary)
            identity = tuple(range(len(primary)))
            for order in topological_orders(len(primary), edges, limit=1001):
                if order != identity:
                    alternative = tuple(primary[index] for index in order)
                    alternative_kind = "commutation"
                    break
        if alternative is None:
            alternative = primary
            alternative_kind = "reference_fallback_no_observed_alternative"
        alternative_execution = execute_plan(problem, alternative)
        if not alternative_execution.valid:
            raise RuntimeError(f"invalid positive control for {queued['source_path']}")
        alternative_po = any(
            matches_partial_order(action_ids(alternative), ref, dependency_edges(ref))
            for ref in references
        )

        deletion = None
        deletion_execution = None
        deletion_index = None
        for index in range(len(primary) - 1, -1, -1):
            candidate = primary[:index] + primary[index + 1 :]
            execution = execute_plan(problem, candidate)
            if not execution.valid:
                deletion = candidate
                deletion_execution = execution
                deletion_index = index
                break
        if deletion is None or deletion_execution is None:
            raise RuntimeError(f"no invalid deletion control for {queued['source_path']}")

        tasks.append(
            {
                "source_path": queued["source_path"],
                "reference": list(action_ids(primary)),
                "positive_alternative": {
                    "kind": alternative_kind,
                    "plan": list(action_ids(alternative)),
                    "exact_match": action_ids(alternative) == action_ids(primary),
                    "partial_order_match": alternative_po,
                    "goal_valid": alternative_execution.valid,
                },
                "deletion_negative": {
                    "deleted_index": deletion_index,
                    "plan": list(action_ids(deletion)),
                    "executable": deletion_execution.executable,
                    "goal_satisfied": deletion_execution.goal_satisfied,
                    "valid": deletion_execution.valid,
                    "failure_step": deletion_execution.failure_step,
                    "failed_action_id": deletion_execution.failed_action_id,
                    "missing_preconditions": sorted(
                        map(str, deletion_execution.missing_preconditions)
                    ),
                },
            }
        )

    alternatives = [task["positive_alternative"] for task in tasks]
    available = [
        item
        for item in alternatives
        if item["kind"] != "reference_fallback_no_observed_alternative"
    ]
    negatives = [task["deletion_negative"] for task in tasks]
    summary = {
        "task_count": len(tasks),
        "tasks_with_nonreference_positive": len(available),
        "positive_goal_valid_rate": sum(item["goal_valid"] for item in alternatives)
        / len(alternatives),
        "positive_partial_order_match_rate": sum(
            item["partial_order_match"] for item in alternatives
        )
        / len(alternatives),
        "positive_exact_match_rate": sum(item["exact_match"] for item in alternatives)
        / len(alternatives),
        "single_reference_false_rejection_on_nonreference_positives": (
            sum(not item["exact_match"] for item in available) / len(available)
            if available
            else None
        ),
        "deletion_negative_rejection_rate": sum(not item["valid"] for item in negatives)
        / len(negatives),
        "deletion_precondition_failure_count": sum(
            not item["executable"] for item in negatives
        ),
        "deletion_goal_miss_count": sum(
            item["executable"] and not item["goal_satisfied"] for item in negatives
        ),
    }
    report = {
        "evidence_status": args.evidence_status,
        "control_version": args.control_version,
        "queue_version": queue["queue_version"],
        "summary": summary,
        "tasks": tasks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.table_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Deterministic 100-task controls",
        "",
        args.table_boundary,
        "",
        "| Control | Tasks | Goal valid | Partial-order match | Exact match |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Valid alternative/fallback | {len(tasks)} | {summary['positive_goal_valid_rate']:.2%} | "
        f"{summary['positive_partial_order_match_rate']:.2%} | {summary['positive_exact_match_rate']:.2%} |",
        f"| Required-action deletion | {len(tasks)} | {1-summary['deletion_negative_rejection_rate']:.2%} | -- | -- |",
        "",
        f"Non-reference positive controls: {len(available)}/{len(tasks)}; exact-match false rejection on that supported subset: "
        f"{summary['single_reference_false_rejection_on_nonreference_positives']:.2%}.",
        "",
        f"Deletion failures: {summary['deletion_precondition_failure_count']} precondition failures and "
        f"{summary['deletion_goal_miss_count']} executable goal misses.",
    ]
    args.table_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
