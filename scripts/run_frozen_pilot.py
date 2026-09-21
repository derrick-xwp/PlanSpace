"""Run a frozen-source task through candidate PlanSpace semantics."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import enumerate_valid_plans, execute_plan
from planspace.metrics import false_rejection_rate
from planspace.partial_order import dependency_edges, validate_topological_orders
from planspace.pilot_domains import (
    ACTION_DOMAIN_VERSION,
    installing_a_printer_problem,
    moving_boxes_to_storage_problem,
    opening_doors_problem,
    organizing_file_cabinet_problem,
    storing_food_problem,
)


EXPECTED_SOURCE_SHA256 = {
    "installing_a_printer": "8701a201851baeed1b8a918d1c03ac3739cff6a8ac5b2d5109df1ce8f4cdbb0a",
    "opening_doors": "0051d08c1826ceb8eaf9ca5ab595c14fd539d8b162a42293ab48be8134bbc719",
    "organizing_file_cabinet": "75346b08e46b67d98660fda3197caef802d0412ea60008cd27634fe0cba2008d",
    "moving_boxes_to_storage": "13c91058b0266345eec5a5019b3882f1a1ff794dec5643548b2d42927b700995",
    "storing_food": "501ba590cc5699a4f89f20ed68d6ea7d3baccc7adbacd441999e86ed2b934ef3",
}
ADAPTERS = {
    "installing_a_printer": (installing_a_printer_problem, 2, False, None),
    "moving_boxes_to_storage": (moving_boxes_to_storage_problem, 3, False, None),
    "opening_doors": (opening_doors_problem, 4, False, None),
    "organizing_file_cabinet": (organizing_file_cabinet_problem, 5, False, None),
    "storing_food": (storing_food_problem, 8, True, 1000),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("activity", choices=sorted(EXPECTED_SOURCE_SHA256))
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_hash = sha256(args.source.read_bytes()).hexdigest()
    expected_hash = EXPECTED_SOURCE_SHA256[args.activity]
    if source_hash != expected_hash:
        raise ValueError(
            f"source hash mismatch: expected {expected_hash}, observed {source_hash}"
        )

    source = parse_problem_file(args.source)
    adapter, max_depth, deduplicate_states, topological_limit = ADAPTERS[args.activity]
    problem = adapter(source)
    enumeration = enumerate_valid_plans(
        problem,
        max_depth=max_depth,
        deduplicate_states=deduplicate_states,
    )
    plans = [list(action.action_id for action in plan) for plan in enumeration.plans]
    if not enumeration.plans:
        raise RuntimeError("candidate semantics produced no valid plans")

    family_records = []
    for plan in enumeration.plans:
        execution = execute_plan(problem, plan)
        edges = dependency_edges(plan)
        valid_sorts, total_sorts = validate_topological_orders(
            problem, plan, edges, limit=topological_limit
        )
        family_records.append(
            {
                "plan": [action.action_id for action in plan],
                "execution_valid": execution.valid,
                "partial_order_edges": [list(edge) for edge in sorted(edges)],
                "valid_topological_sorts": valid_sorts,
                "total_topological_sorts": total_sorts,
                "topological_validation_status": (
                    "sampled" if topological_limit is not None else "complete"
                ),
            }
        )

    negative_records = []
    seen_negative_ids = set()
    for plan in enumeration.plans:
        mutations = []
        for index in range(len(plan)):
            mutations.append(plan[:index] + plan[index + 1 :])
        for index in range(len(plan) - 1):
            swapped = list(plan)
            swapped[index], swapped[index + 1] = swapped[index + 1], swapped[index]
            mutations.append(tuple(swapped))
        for candidate in mutations:
            candidate_ids = tuple(action.action_id for action in candidate)
            if candidate_ids in seen_negative_ids:
                continue
            seen_negative_ids.add(candidate_ids)
            execution = execute_plan(problem, candidate)
            if execution.valid:
                continue
            negative_records.append(
                {
                    "plan": list(candidate_ids),
                    "executable": execution.executable,
                    "goal_satisfied": execution.goal_satisfied,
                    "failure_step": execution.failure_step,
                    "failed_action_id": execution.failed_action_id,
                    "missing_preconditions": sorted(
                        str(predicate) for predicate in execution.missing_preconditions
                    ),
                }
            )
            if len(negative_records) >= 10:
                break
        if len(negative_records) >= 10:
            break

    report = {
        "evidence_status": "frozen_bddl_candidate_semantics_not_paper_evidence",
        "activity": args.activity,
        "problem_id": problem.problem_id,
        "source_sha256": source_hash,
        "action_domain_version": ACTION_DOMAIN_VERSION,
        "plan_count": len(plans),
        "enumeration_unit": (
            "unique_final_state_representatives"
            if deduplicate_states
            else "simple_plan_sequences"
        ),
        "plan_lengths": sorted(len(plan) for plan in plans),
        "completeness_status": enumeration.completeness_status,
        "search_bound": {"max_depth": max_depth, "max_cost": None},
        "single_reference_false_rejection_rate": false_rejection_rate(
            problem, enumeration.plans, enumeration.plans[0]
        ),
        "families": family_records,
        "structured_negative_count": len(negative_records),
        "structured_negatives": negative_records,
        "audit_requirement": "manual trace review and action-semantic sign-off",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
