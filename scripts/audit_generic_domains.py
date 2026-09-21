#!/usr/bin/env python3
"""Build and validate candidate generic domains for a frozen review queue."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import action_ids, execute_plan
from planspace.generic_domain import (
    GENERIC_DOMAIN_VERSION,
    construct_goal_plan,
    generic_household_problem,
)
from planspace.partial_order import dependency_edges, validate_topological_orders


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--topological-limit", type=int, default=1000)
    args = parser.parse_args()

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    task_records = []
    for queued in queue["records"]:
        source_path = args.source_root / queued["source_path"]
        observed_hash = sha256(source_path.read_bytes()).hexdigest()
        record = {
            "problem_name": queued["problem_name"],
            "source_path": queued["source_path"],
            "source_sha256": observed_hash,
            "source_hash_matches_queue": observed_hash == queued["source_sha256"],
            "goal_alternative_count": queued["goal_alternative_count"],
            "status": None,
            "operator_vocabulary": [],
            "action_count": None,
            "solved_goal_alternative_count": 0,
            "unique_plan_representative_count": 0,
            "plan_length_min": None,
            "plan_length_max": None,
            "all_stored_plans_validate": False,
            "topological_orders_checked": 0,
            "topological_orders_valid": 0,
            "errors": [],
        }
        try:
            if not record["source_hash_matches_queue"]:
                raise ValueError("raw-source hash differs from frozen queue")
            problem = generic_household_problem(parse_problem_file(source_path))
            record["operator_vocabulary"] = sorted(
                {action.operator for action in problem.actions}
            )
            record["action_count"] = len(problem.actions)
            plans = []
            for goal_index, goal in enumerate(problem.goal_alternatives):
                try:
                    plan = construct_goal_plan(problem, goal)
                    if not execute_plan(problem, plan).valid:
                        raise ValueError("constructed plan failed full problem validation")
                    plans.append(plan)
                except Exception as error:
                    if len(record["errors"]) < 10:
                        record["errors"].append(
                            f"goal_{goal_index}: {type(error).__name__}: {error}"
                        )
            unique = {}
            for plan in plans:
                unique.setdefault(action_ids(plan), plan)
            checked = valid = 0
            for plan in unique.values():
                edges = dependency_edges(plan)
                plan_valid, plan_checked = validate_topological_orders(
                    problem, plan, edges, limit=args.topological_limit
                )
                checked += plan_checked
                valid += plan_valid
            lengths = [len(plan) for plan in unique.values()]
            record.update(
                {
                    "solved_goal_alternative_count": len(plans),
                    "unique_plan_representative_count": len(unique),
                    "plan_length_min": min(lengths) if lengths else None,
                    "plan_length_max": max(lengths) if lengths else None,
                    "all_stored_plans_validate": bool(plans)
                    and all(execute_plan(problem, plan).valid for plan in unique.values()),
                    "topological_orders_checked": checked,
                    "topological_orders_valid": valid,
                }
            )
            if len(plans) == len(problem.goal_alternatives):
                record["status"] = "candidate_supported_all_goal_alternatives"
            elif plans:
                record["status"] = "candidate_supported_satisfiable_subset"
            else:
                record["status"] = "candidate_unsupported"
        except Exception as error:
            record["status"] = "candidate_unsupported"
            record["errors"].append(f"{type(error).__name__}: {error}")
        task_records.append(record)
        print(record["source_path"], record["status"], flush=True)

    fully_supported = [
        record
        for record in task_records
        if record["status"] == "candidate_supported_all_goal_alternatives"
    ]
    supported = [
        record
        for record in task_records
        if record["status"].startswith("candidate_supported_")
    ]
    representatives = sum(
        record["unique_plan_representative_count"] for record in supported
    )
    exact_rejected = sum(
        max(0, record["unique_plan_representative_count"] - 1)
        for record in supported
    )
    summary = {
        "queue_task_count": len(task_records),
        "fully_candidate_supported_task_count": len(fully_supported),
        "satisfiable_subset_task_count": sum(
            record["status"] == "candidate_supported_satisfiable_subset"
            for record in task_records
        ),
        "candidate_unsupported_task_count": sum(
            record["status"] == "candidate_unsupported" for record in task_records
        ),
        "tasks_with_multiple_goal_plan_representatives": sum(
            record["unique_plan_representative_count"] > 1
            for record in supported
        ),
        "tasks_with_commutation_multiplicity": sum(
            record["topological_orders_checked"]
            > record["unique_plan_representative_count"]
            for record in supported
        ),
        "tasks_with_any_observed_multiplicity": sum(
            record["unique_plan_representative_count"] > 1
            or record["topological_orders_checked"]
            > record["unique_plan_representative_count"]
            for record in supported
        ),
        "tasks_hitting_topological_sample_limit": sum(
            record["topological_orders_checked"]
            >= args.topological_limit * record["unique_plan_representative_count"]
            for record in supported
        ),
        "unique_goal_plan_representative_count": representatives,
        "single_reference_false_rejection_over_goal_representatives": (
            exact_rejected / representatives if representatives else None
        ),
        "all_stored_plans_validate": bool(supported)
        and all(record["all_stored_plans_validate"] for record in supported),
        "topological_orders_checked": sum(
            record["topological_orders_checked"] for record in supported
        ),
        "topological_orders_valid": sum(
            record["topological_orders_valid"] for record in supported
        ),
    }
    report = {
        "evidence_status": "generic_candidate_domains_pending_independent_semantic_review",
        "audit_version": "planspace_generic_domain_audit_v0.1",
        "generic_domain_version": GENERIC_DOMAIN_VERSION,
        "topological_validation_limit_per_representative": args.topological_limit,
        "summary": summary,
        "tasks": task_records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
