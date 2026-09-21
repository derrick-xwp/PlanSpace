#!/usr/bin/env python3
"""Generate the deterministic five-pilot action-abstraction audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from planspace.action_abstraction import (
    ACTION_ABSTRACTION_VERSION,
    CANONICAL_OPERATORS,
    OPERATOR_ALIASES,
    summarize_action_abstraction,
)
from planspace.bddl_parser import parse_problem_file
from planspace.pilot_domains import (
    installing_a_printer_problem,
    moving_boxes_to_storage_problem,
    opening_doors_problem,
    organizing_file_cabinet_problem,
    storing_food_problem,
)


ADAPTERS = (
    ("opening_doors", "opening_doors_problem0.bddl", opening_doors_problem),
    (
        "installing_a_printer",
        "installing_a_printer_problem0.bddl",
        installing_a_printer_problem,
    ),
    (
        "organizing_file_cabinet",
        "organizing_file_cabinet_problem0.bddl",
        organizing_file_cabinet_problem,
    ),
    (
        "moving_boxes_to_storage",
        "moving_boxes_to_storage_problem0.bddl",
        moving_boxes_to_storage_problem,
    ),
    ("storing_food", "storing_food_problem0.bddl", storing_food_problem),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("tests/fixtures/behavior_v3_9_2"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/action_abstraction_audit_v0_1.json"),
    )
    args = parser.parse_args()

    problems = []
    for task, filename, adapter in ADAPTERS:
        problems.append((task, adapter(parse_problem_file(args.fixtures / filename))))
    records = summarize_action_abstraction(problems)
    counts: dict[str, int] = {}
    for record in records:
        counts[record.status] = counts.get(record.status, 0) + 1

    payload = {
        "schema_version": "planspace_action_abstraction_audit_v0.1",
        "contract_version": ACTION_ABSTRACTION_VERSION,
        "evidence_status": "candidate_structural_audit_not_semantic_signoff",
        "primary_track": "grounded_high_level_skill_planning",
        "canonical_operators": sorted(CANONICAL_OPERATORS),
        "aliases": dict(sorted(OPERATOR_ALIASES.items())),
        "summary": dict(sorted(counts.items())),
        "tasks": [record.to_dict() for record in records],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
