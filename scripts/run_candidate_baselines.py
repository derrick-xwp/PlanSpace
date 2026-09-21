"""Run deterministic non-model sanity controls on the five candidate domains."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random

from planspace.bddl_parser import parse_problem_file
from planspace.candidate_experiments import (
    evaluate_predictions,
    random_action_plan,
    random_enabled_plan,
)
from planspace.core import action_ids, enumerate_valid_plans
from planspace.pilot_domains import (
    ACTION_DOMAIN_VERSION,
    installing_a_printer_problem,
    moving_boxes_to_storage_problem,
    opening_doors_problem,
    organizing_file_cabinet_problem,
    storing_food_problem,
)


SPECS = {
    "installing_a_printer": (installing_a_printer_problem, 2, False),
    "opening_doors": (opening_doors_problem, 4, False),
    "moving_boxes_to_storage": (moving_boxes_to_storage_problem, 3, False),
    "organizing_file_cabinet": (organizing_file_cabinet_problem, 5, False),
    "storing_food": (storing_food_problem, 8, True),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260914)
    args = parser.parse_args()

    task_records = []
    aggregate_inputs = {}
    for task_index, (activity, spec) in enumerate(SPECS.items()):
        adapter, max_depth, deduplicate_states = spec
        source = parse_problem_file(args.fixture_root / f"{activity}_problem0.bddl")
        problem = adapter(source)
        enumeration = enumerate_valid_plans(
            problem,
            max_depth=max_depth,
            deduplicate_states=deduplicate_states,
        )
        reference = enumeration.plans[0]
        alternative = next(
            (
                plan
                for plan in reversed(enumeration.plans)
                if action_ids(plan) != action_ids(reference)
            ),
            reference,
        )
        rng = random.Random(args.seed + task_index)
        predictions = {
            "reference_replay_control": [reference],
            "oracle_alternative_control": [alternative],
            "random_action_control": [
                random_action_plan(problem, max_depth=max_depth, rng=rng)
                for _ in range(args.trials)
            ],
            "random_enabled_control": [
                random_enabled_plan(problem, max_depth=max_depth, rng=rng)
                for _ in range(args.trials)
            ],
        }
        metrics = {
            name: evaluate_predictions(problem, plans, reference)
            for name, plans in predictions.items()
        }
        task_records.append(
            {
                "activity": activity,
                "reference": list(action_ids(reference)),
                "candidate_valid_plan_count": len(enumeration.plans),
                "controls": metrics,
            }
        )
        for name, values in metrics.items():
            aggregate = aggregate_inputs.setdefault(
                name,
                {"attempts": 0, "exact": 0.0, "executable": 0.0, "goal": 0.0},
            )
            aggregate["attempts"] += values["attempts"]
            aggregate["exact"] += values["exact_match_rate"] * values["attempts"]
            aggregate["executable"] += values["executable_rate"] * values["attempts"]
            aggregate["goal"] += values["goal_success_rate"] * values["attempts"]

    aggregate = {}
    for name, values in aggregate_inputs.items():
        attempts = values["attempts"]
        aggregate[name] = {
            "attempts": attempts,
            "exact_match_rate": values["exact"] / attempts,
            "executable_rate": values["executable"] / attempts,
            "goal_success_rate": values["goal"] / attempts,
        }
    report = {
        "evidence_status": "candidate_semantics_sanity_controls_not_model_results",
        "action_domain_version": ACTION_DOMAIN_VERSION,
        "seed": args.seed,
        "random_trials_per_task": args.trials,
        "control_definitions": {
            "reference_replay_control": "replay the first enumerated valid plan",
            "oracle_alternative_control": (
                "use a different enumerated valid plan when one exists; this is an "
                "evaluation sanity check, not a planner"
            ),
            "random_action_control": "sample actions without checking applicability",
            "random_enabled_control": (
                "sample only currently applicable actions and stop on goal or depth bound"
            ),
        },
        "aggregate_micro": aggregate,
        "tasks": task_records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "tasks"}, indent=2))


if __name__ == "__main__":
    main()
