#!/usr/bin/env python3
"""Discover goal-reaching plans without using reference constructors or DAGs.

The search consumes only the frozen grounded action model. Frozen references are
loaded after discovery solely to classify independently found plans as exact or
non-reference. This is algorithmic independence, not external semantic
validation of the action abstraction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from heapq import heappop, heappush
from itertools import count
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import PlanningProblem, State, action_ids, execute_plan
from planspace.generic_domain import generic_household_problem


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independent_search(
    problem: PlanningProblem,
    *,
    max_depth: int,
    max_solutions: int,
    max_expanded: int,
    paths_per_state: int,
    cost_slack: float,
) -> dict:
    """Uniform-cost simple-path search over frozen grounded actions.

    No reference plan, partial-order edge, or deterministic control is an input.
    A bounded number of distinct paths may reach the same state so commuting
    solutions are not collapsed by ordinary graph-search deduplication.
    """

    serial = count()
    queue: list[tuple[float, int, int, State, tuple, frozenset[State]]] = []
    heappush(
        queue,
        (0.0, 0, next(serial), problem.initial_state, tuple(), frozenset({problem.initial_state})),
    )
    visits: dict[State, int] = defaultdict(int)
    solutions: dict[tuple[str, ...], tuple] = {}
    expanded = 0
    minimum_goal_cost: float | None = None
    termination = "search_exhausted"
    actions = tuple(sorted(problem.actions, key=lambda item: item.action_id))

    while queue:
        cost, depth, _, state, plan, path_states = heappop(queue)
        if minimum_goal_cost is not None and cost > minimum_goal_cost + cost_slack:
            termination = "cost_slack_exhausted"
            break
        if problem.goal_satisfied(state):
            key = action_ids(plan)
            solutions.setdefault(key, plan)
            if minimum_goal_cost is None:
                minimum_goal_cost = cost
            if len(solutions) >= max_solutions:
                termination = "max_solutions_reached"
                break
            continue
        if depth >= max_depth:
            continue
        if visits[state] >= paths_per_state:
            continue
        visits[state] += 1
        expanded += 1
        if expanded >= max_expanded:
            termination = "max_expanded_reached"
            break
        for action in actions:
            if not action.enabled(state):
                continue
            next_state = action.apply(state)
            if next_state in path_states:
                continue
            heappush(
                queue,
                (
                    cost + action.cost,
                    depth + 1,
                    next(serial),
                    next_state,
                    plan + (action,),
                    path_states | {next_state},
                ),
            )

    verified = []
    for key, plan in sorted(solutions.items(), key=lambda item: (len(item[0]), item[0])):
        replay = execute_plan(problem, plan)
        if not replay.valid:
            raise RuntimeError(f"search emitted invalid plan for {problem.problem_id}: {key}")
        verified.append(list(key))
    return {
        "solution_count": len(verified),
        "minimum_goal_cost": minimum_goal_cost,
        "expanded_nodes": expanded,
        "termination_reason": termination,
        "search_complete_within_bounds": termination == "search_exhausted",
        "solutions": verified,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("reference_artifact", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--max-solutions", type=int, default=64)
    parser.add_argument("--max-expanded", type=int, default=200000)
    parser.add_argument("--paths-per-state", type=int, default=16)
    parser.add_argument("--cost-slack", type=float, default=2.0)
    args = parser.parse_args()

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    frozen = json.loads(args.reference_artifact.read_text(encoding="utf-8"))
    reference_by_path = {task["source_path"]: tuple(task["reference_plan"]) for task in frozen["tasks"]}
    if set(reference_by_path) != {row["source_path"] for row in queue["records"]}:
        raise ValueError("queue and frozen reference artifact task sets differ")

    tasks = []
    for index, row in enumerate(queue["records"], start=1):
        source_path = args.source_root / row["source_path"]
        if sha256(source_path) != row["source_sha256"]:
            raise ValueError(f"source hash mismatch: {row['source_path']}")
        problem = generic_household_problem(parse_problem_file(source_path))
        result = independent_search(
            problem,
            max_depth=args.max_depth,
            max_solutions=args.max_solutions,
            max_expanded=args.max_expanded,
            paths_per_state=args.paths_per_state,
            cost_slack=args.cost_slack,
        )
        reference = reference_by_path[row["source_path"]]
        solutions = [tuple(plan) for plan in result.pop("solutions")]
        nonreference = [plan for plan in solutions if plan != reference]
        tasks.append(
            {
                "source_path": row["source_path"],
                "source_sha256": row["source_sha256"],
                **result,
                "reference_disclosed_to_search": False,
                "reference_found": reference in solutions,
                "nonreference_solution_count": len(nonreference),
                "nonreference_examples": [list(plan) for plan in nonreference[:5]],
            }
        )
        print(f"[{index}/{len(queue['records'])}] {row['source_path']}: {len(solutions)} solutions", flush=True)

    solved = [task for task in tasks if task["solution_count"]]
    alternatives = [task for task in tasks if task["nonreference_solution_count"]]
    summary = {
        "task_count": len(tasks),
        "tasks_with_independent_solution": len(solved),
        "tasks_with_independent_nonreference_solution": len(alternatives),
        "independent_solution_count": sum(task["solution_count"] for task in tasks),
        "independent_nonreference_solution_count": sum(task["nonreference_solution_count"] for task in tasks),
        "tasks_hitting_resource_bound": sum(
            task["termination_reason"] in {"max_solutions_reached", "max_expanded_reached"}
            for task in tasks
        ),
    }
    report = {
        "evidence_status": "post_hoc_independent_algorithmic_validation",
        "analysis_version": "planspace-independent-state-search-v0.1",
        "independence_boundary": (
            "The search never consumes reference plans, reference DAGs, or deterministic controls. "
            "It shares the frozen grounded action semantics and goal predicate with the evaluator, "
            "so it is an independent search implementation rather than external semantic validation."
        ),
        "inputs": {
            "queue": str(args.queue),
            "queue_sha256": sha256(args.queue),
            "reference_artifact": str(args.reference_artifact),
            "reference_artifact_sha256": sha256(args.reference_artifact),
        },
        "bounds": {
            "max_depth": args.max_depth,
            "max_solutions": args.max_solutions,
            "max_expanded": args.max_expanded,
            "paths_per_state": args.paths_per_state,
            "cost_slack": args.cost_slack,
            "path_policy": "simple symbolic state paths",
        },
        "summary": summary,
        "tasks": tasks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output:
        lines = [
            "# Independent state-space search audit",
            "",
            report["independence_boundary"],
            "",
            f"- Tasks: {summary['task_count']}",
            f"- Tasks with an independently discovered solution: {summary['tasks_with_independent_solution']}",
            f"- Tasks with an independently discovered non-reference solution: {summary['tasks_with_independent_nonreference_solution']}",
            f"- Distinct discovered solutions: {summary['independent_solution_count']}",
            f"- Distinct non-reference solutions: {summary['independent_nonreference_solution_count']}",
            f"- Tasks hitting a resource bound: {summary['tasks_hitting_resource_bound']}",
        ]
        args.markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
