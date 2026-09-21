#!/usr/bin/env python3
"""Measure constructed-family coverage on tasks with exhaustive bounded search."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import action_ids, enumerate_valid_plans
from planspace.generic_domain import construct_goal_plan, generic_household_problem
from planspace.partial_order import dependency_edges, topological_orders


def known_family_plans(problem, representatives, *, limit: int) -> tuple[set[tuple[str, ...]], bool]:
    known: set[tuple[str, ...]] = set()
    for plan in representatives:
        edges = dependency_edges(plan)
        count = 0
        for order in topological_orders(len(plan), edges, limit=limit):
            count += 1
            known.add(tuple(plan[index].action_id for index in order))
        if count >= limit:
            return known, False
    return known, True


def task_coverage(
    problem, *, max_depth: int, max_plans: int, representatives=None
) -> dict:
    if representatives is None:
        unique_representatives = {}
        for goal in problem.goal_alternatives:
            try:
                plan = construct_goal_plan(problem, goal)
            except Exception:
                continue
            unique_representatives.setdefault(action_ids(plan), plan)
        representatives = list(unique_representatives.values())
    known, family_exhaustive = known_family_plans(
        problem, representatives, limit=max_plans
    )
    enumeration = enumerate_valid_plans(
        problem,
        max_depth=max_depth,
        max_plans=max_plans,
        deduplicate_states=False,
    )
    valid = {action_ids(plan) for plan in enumeration.plans}
    search_exhaustive = enumeration.completeness_status == "bounded_complete_simple_paths"
    matched = valid & known
    missed = sorted(valid - known)
    return {
        "max_depth": max_depth,
        "expanded_nodes": enumeration.expanded_nodes,
        "search_exhaustive": search_exhaustive,
        "family_order_enumeration_exhaustive": family_exhaustive,
        "bounded_valid_plan_count": len(valid),
        "known_family_plan_count": len(known),
        "bounded_valid_plan_covered_count": len(matched),
        "bounded_family_coverage": len(matched) / len(valid) if valid else None,
        "bounded_valid_plans_outside_families_count": len(missed),
        "outside_family_examples": [list(plan) for plan in missed[:10]],
    }


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    incomplete = [
        task
        for task in report["tasks"]
        if task["search_exhaustive"]
        and task["family_order_enumeration_exhaustive"]
        and task["bounded_family_coverage"] != 1.0
    ]
    lines = [
        "# PlanSpace bounded reference-family coverage v0.1",
        "",
        f"Evidence status: `{report['evidence_status']}`.",
        "",
        "## Exhaustive bounded subset",
        "",
        f"- Queue tasks: {summary['queue_task_count']}",
        f"- Exhaustively analyzed within the declared bounds: {summary['exhaustively_analyzed_task_count']}",
        f"- Bounded first-goal simple paths: {summary['bounded_valid_plan_count']}",
        f"- Paths covered by constructed reference families: {summary['bounded_valid_plan_covered_count']}",
        f"- Micro coverage: {summary['micro_bounded_family_coverage'] * 100:.2f}%",
        f"- Tasks with full bounded coverage: {summary['tasks_with_full_bounded_coverage']}",
        "",
        "## Tasks with bounded coverage below 100%",
        "",
        "| Task | Valid paths | Covered | Coverage | Outside family |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for task in incomplete:
        lines.append(
            f"| `{task['source_path']}` | {task['bounded_valid_plan_count']} | "
            f"{task['bounded_valid_plan_covered_count']} | "
            f"{task['bounded_family_coverage'] * 100:.2f}% | "
            f"{task['bounded_valid_plans_outside_families_count']} |"
        )
    lines.extend(
        [
            "",
            "The only incomplete case uses an existential refrigerator binding while a separate "
            "concrete refrigerator has a negative open-state goal. The extra bounded paths insert "
            "goal-irrelevant open/close actions around an otherwise valid wildcard-binding plan; "
            "the constructed families intentionally retain causal representatives rather than all "
            "nonminimal detours.",
            "",
            "## Boundary",
            "",
            report["boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--max-actions", type=int, default=12)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--max-plans", type=int, default=100000)
    args = parser.parse_args()

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    records = []
    excluded = []
    for queued in queue["records"]:
        source = parse_problem_file(args.source_root / queued["source_path"])
        problem = generic_household_problem(source)
        representative_lengths = []
        for goal in problem.goal_alternatives:
            try:
                representative_lengths.append(len(construct_goal_plan(problem, goal)))
            except Exception:
                pass
        required_depth = max(representative_lengths) if representative_lengths else None
        reason = None
        if required_depth is None:
            reason = "no_constructed_representative"
        elif len(problem.actions) > args.max_actions:
            reason = "action_count_above_limit"
        elif required_depth > args.max_depth:
            reason = "reference_depth_above_limit"
        if reason is not None:
            excluded.append(
                {
                    "source_path": queued["source_path"],
                    "reason": reason,
                    "action_count": len(problem.actions),
                    "required_depth": required_depth,
                }
            )
            continue
        result = task_coverage(
            problem,
            max_depth=required_depth,
            max_plans=args.max_plans,
        )
        result.update(
            {
                "source_path": queued["source_path"],
                "action_count": len(problem.actions),
            }
        )
        records.append(result)
        print(queued["source_path"], result["bounded_family_coverage"], flush=True)

    complete = [
        record
        for record in records
        if record["search_exhaustive"]
        and record["family_order_enumeration_exhaustive"]
    ]
    valid_total = sum(record["bounded_valid_plan_count"] for record in complete)
    covered_total = sum(
        record["bounded_valid_plan_covered_count"] for record in complete
    )
    report = {
        "evidence_status": "bounded_symbolic_family_coverage_pending_semantic_review",
        "analysis_version": "planspace-bounded-family-coverage-v0.1",
        "bounds": {
            "max_actions": args.max_actions,
            "max_reference_depth": args.max_depth,
            "max_plans_per_search_or_family": args.max_plans,
            "path_policy": "first goal-reaching simple state paths",
        },
        "summary": {
            "queue_task_count": len(queue["records"]),
            "attempted_task_count": len(records),
            "exhaustively_analyzed_task_count": len(complete),
            "excluded_task_count": len(excluded),
            "bounded_valid_plan_count": valid_total,
            "bounded_valid_plan_covered_count": covered_total,
            "micro_bounded_family_coverage": (
                covered_total / valid_total if valid_total else None
            ),
            "tasks_with_full_bounded_coverage": sum(
                record["bounded_family_coverage"] == 1.0 for record in complete
            ),
        },
        "tasks": records,
        "excluded_tasks": excluded,
        "boundary": (
            "Completeness applies only to first goal-reaching simple symbolic paths within each "
            "reported depth bound. It neither covers arbitrary nonminimal loops nor validates "
            "the real-world faithfulness of the action abstraction."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output is not None:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "boundary": report["boundary"]}, indent=2))


if __name__ == "__main__":
    main()
