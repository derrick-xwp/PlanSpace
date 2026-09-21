#!/usr/bin/env python3
"""Audit topological-order validation caps on the current 171-task suite."""

from __future__ import annotations

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import action_ids, execute_plan
from planspace.generic_domain import construct_goal_plan, generic_household_problem
from planspace.partial_order import dependency_edges, topological_orders


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_topological_order_count(node_count: int, edges: frozenset[tuple[int, int]]) -> int:
    predecessor_masks = [0] * node_count
    for left, right in edges:
        predecessor_masks[right] |= 1 << left

    @lru_cache(maxsize=None)
    def visit(remaining: int) -> int:
        if remaining == 0:
            return 1
        total = 0
        for node in range(node_count):
            bit = 1 << node
            if remaining & bit and predecessor_masks[node] & remaining == 0:
                total += visit(remaining ^ bit)
        return total

    return visit((1 << node_count) - 1)


def validate_topological_caps(problem, plan, edges, caps: list[int]) -> list[dict]:
    """Replay topological orders incrementally in lexical DFS order.

    This has the same order as ``topological_orders`` but shares execution work
    across common prefixes instead of replaying each full plan from the initial
    state.
    """

    node_count = len(plan)
    predecessor_masks = [0] * node_count
    for left, right in edges:
        predecessor_masks[right] |= 1 << left
    maximum = caps[-1]
    checked = 0
    valid = 0
    snapshots: dict[int, tuple[int, int]] = {}

    @lru_cache(maxsize=None)
    def completion_count(remaining: int) -> int:
        if remaining == 0:
            return 1
        total = 0
        for node in range(node_count):
            bit = 1 << node
            if remaining & bit and predecessor_masks[node] & remaining == 0:
                total += completion_count(remaining ^ bit)
        return total

    def record_crossed(previous: int) -> None:
        for cap in caps:
            if previous < cap <= checked and cap not in snapshots:
                snapshots[cap] = (cap, valid)

    def visit(remaining: int, state) -> None:
        nonlocal checked, valid
        if checked >= maximum:
            return
        if remaining == 0:
            previous = checked
            checked += 1
            valid += int(problem.goal_satisfied(state))
            record_crossed(previous)
            return
        for node in range(node_count):
            if checked >= maximum:
                return
            bit = 1 << node
            if not remaining & bit or predecessor_masks[node] & remaining:
                continue
            action = plan[node]
            if action.enabled(state):
                visit(remaining ^ bit, action.apply(state))
            else:
                previous = checked
                checked += min(maximum - checked, completion_count(remaining ^ bit))
                record_crossed(previous)

    visit((1 << node_count) - 1, problem.initial_state)
    rows = []
    for cap in caps:
        observed_checked, observed_valid = snapshots.get(cap, (checked, valid))
        rows.append(
            {
                "cap": cap,
                "checked": observed_checked,
                "valid": observed_valid,
                "all_valid": observed_checked == observed_valid,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--caps", nargs="+", type=int, default=[100, 500, 1000, 2000, 5000])
    args = parser.parse_args()
    caps = sorted(set(args.caps))
    if not caps or caps[0] <= 0:
        raise ValueError("caps must be positive")

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    records = []
    total_representatives = 0
    multiplicity_tasks = 0
    for row in queue["records"]:
        records_before_task = len(records)
        source_path = args.source_root / row["source_path"]
        if sha256(source_path) != row["source_sha256"]:
            raise ValueError(f"source hash mismatch: {row['source_path']}")
        problem = generic_household_problem(parse_problem_file(source_path))
        unique = {}
        for goal in problem.goal_alternatives:
            try:
                plan = construct_goal_plan(problem, goal)
            except Exception:
                continue
            if execute_plan(problem, plan).valid:
                unique.setdefault(action_ids(plan), plan)
        for representative_index, plan in enumerate(unique.values()):
            total_representatives += 1
            edges = dependency_edges(plan)
            first_thousand = list(topological_orders(len(plan), edges, limit=1000))
            if len(first_thousand) < 1000:
                continue
            exact_count = exact_topological_order_count(len(plan), edges)
            cap_rows = validate_topological_caps(problem, plan, edges, caps)
            records.append(
                {
                    "source_path": row["source_path"],
                    "representative_index": representative_index,
                    "plan_length": len(plan),
                    "exact_topological_order_count": exact_count,
                    "cap_results": cap_rows,
                }
            )
        if len(unique) > 1 or any(
            len(list(topological_orders(len(plan), dependency_edges(plan), limit=2))) > 1
            for plan in unique.values()
        ):
            multiplicity_tasks += 1
        if len(records) > records_before_task:
            print(f"{row['source_path']}: cumulative capped representatives={len(records)}", flush=True)

    summary = {
        "task_count": len(queue["records"]),
        "unique_goal_plan_representative_count": total_representatives,
        "tasks_with_observed_family_multiplicity": multiplicity_tasks,
        "capped_representative_count": len(records),
        "capped_task_count": len({row["source_path"] for row in records}),
        "all_checked_orders_valid_at_every_cap": all(
            cap["all_valid"] for row in records for cap in row["cap_results"]
        ),
        "maximum_exact_topological_order_count": max(
            (row["exact_topological_order_count"] for row in records), default=0
        ),
    }
    report = {
        "evidence_status": "post_hoc_partial_order_cap_sensitivity",
        "analysis_version": "planspace-partial-order-cap-sensitivity-v0.1",
        "inputs": {"queue": str(args.queue), "queue_sha256": sha256(args.queue)},
        "caps": caps,
        "metric_boundary": (
            "The validation cap limits empirical replay checks of generated topological orders. "
            "Model partial-order membership is computed directly against DAG constraints and does "
            "not enumerate orders, so its reported score is invariant to this cap."
        ),
        "summary": summary,
        "representatives": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output:
        lines = [
            "# Partial-order cap sensitivity",
            "",
            report["metric_boundary"],
            "",
            f"- Current-suite tasks: {summary['task_count']}",
            f"- Representatives reaching the original 1,000-order cap: {summary['capped_representative_count']}",
            f"- Tasks containing such a representative: {summary['capped_task_count']}",
            f"- All checked orders valid at every cap: {summary['all_checked_orders_valid_at_every_cap']}",
            f"- Largest exact number of topological orders: {summary['maximum_exact_topological_order_count']}",
        ]
        args.markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
