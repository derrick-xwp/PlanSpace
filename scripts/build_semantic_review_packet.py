#!/usr/bin/env python3
"""Build a deterministic, stratified packet for independent semantics review."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from hashlib import sha256
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import execute_plan
from planspace.generic_domain import (
    GATED_CONTAINER_TYPES,
    GENERIC_DOMAIN_VERSION,
    construct_goal_plan,
    generic_household_problem,
)
from planspace.translation import goal_quantifier_diagnostics


def action_record(action):
    return {
        "action_id": action.action_id,
        "operator": action.operator,
        "arguments": list(action.args),
        "preconditions": sorted(map(str, action.preconditions)),
        "add_effects": sorted(map(str, action.add_effects)),
        "delete_effects": sorted(map(str, action.delete_effects)),
        "constraints": list(action.constraints),
        "access_sources": list(action.access_sources),
        "access_targets": list(action.access_targets),
        "gated_containers": sorted(action.gated_containers),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("split_manifest", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    parser.add_argument("--per-split", type=int, default=4)
    parser.add_argument(
        "--all-records",
        action="store_true",
        help="review every record in the frozen manifest rather than sampling per split",
    )
    parser.add_argument(
        "--source-overlay",
        type=Path,
        help="optional versioned source-repair tree resolved before source_root",
    )
    args = parser.parse_args()

    manifest = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    grouped = defaultdict(list)
    for record in manifest["records"]:
        grouped[record["split"]].append(record)
    if args.all_records:
        selected = sorted(
            manifest["records"], key=lambda item: (item["source_sha256"], item["source_path"])
        )
        selection_rule = "all records, sorted by source SHA-256 then path"
    else:
        selected = []
        for split in sorted(grouped):
            records = sorted(
                grouped[split], key=lambda item: (item["source_sha256"], item["source_path"])
            )
            if len(records) < args.per_split:
                raise ValueError(f"split {split} has fewer than {args.per_split} tasks")
            selected.extend(records[: args.per_split])
        selection_rule = (
            f"first {args.per_split} tasks per split after sorting by source SHA-256, then path"
        )

    tasks = []
    for selection in selected:
        source_path = args.source_root / selection["source_path"]
        source_overlay = None
        if args.source_overlay is not None:
            candidate = args.source_overlay / selection["source_path"]
            if candidate.exists():
                source_path = candidate
                source_overlay = str(candidate)
        source = parse_problem_file(source_path)
        problem = generic_household_problem(source)
        plans = []
        for goal in problem.goal_alternatives:
            try:
                plan = construct_goal_plan(problem, goal)
            except Exception:
                continue
            execution = execute_plan(problem, plan)
            if execution.valid:
                plans.append((goal, plan, execution))
        if not plans:
            raise RuntimeError(f"no valid review trace for {selection['source_path']}")
        goal, plan, execution = plans[0]
        tasks.append(
            {
                **selection,
                "compiled_source_sha256": sha256(source_path.read_bytes()).hexdigest(),
                "source_overlay": source_overlay,
                "problem_name": source.problem_name,
                "source_objects": [list(item) for item in source.objects],
                "source_initial_expression": source.initial,
                "source_goal_expression": source.goal,
                "source_goal_diagnostics": list(goal_quantifier_diagnostics(source)),
                "compiled_initial_state": sorted(map(str, problem.initial_state)),
                "compiled_goal_alternatives": [
                    sorted(map(str, alternative))
                    for alternative in problem.goal_alternatives
                ],
                "actions": [action_record(action) for action in problem.actions],
                "review_trace": [action.action_id for action in plan],
                "review_trace_states": [
                    sorted(map(str, state)) for state in execution.state_trace
                ],
                "automatic_replay_valid": execution.valid,
                "review": {
                    "source_to_compiled_goal": None,
                    "action_preconditions": None,
                    "action_effects": None,
                    "trace_plausibility_at_declared_abstraction": None,
                    "selective_closed_world_assumptions": None,
                    "decision": None,
                    "reviewer": None,
                    "date": None,
                    "notes": None,
                },
            }
        )

    report = {
        "evidence_status": "unsigned_independent_review_packet",
        "packet_version": "planspace-semantic-review-v0.4",
        "generic_domain_version": GENERIC_DOMAIN_VERSION,
        "semantic_policy_version": "planspace-semantic-policy-v0.4",
        "semantic_policy": {
            "gated_container_types": sorted(GATED_CONTAINER_TYPES),
            "transfer_access": (
                "inside transfers require every directly accessed gated container and "
                "every statically reachable gated ancestor to be open"
            ),
            "spatial_invariants": [
                "spatial_irreflexive",
                "spatial_unique_location",
                "ontop_acyclic",
            ],
            "source_repairs_are_versioned_overlays": True,
            "supported_subtree_transport": (
                "TRANSFER relocates an object's external location while preserving "
                "inside/ontop relations of objects supported by or contained in it"
            ),
        },
        "split_version": manifest["split_version"],
        "selection_rule": selection_rule,
        "task_count": len(tasks),
        "tasks": tasks,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# PlanSpace stratified semantics review packet v0.2",
        "",
        "This packet is unsigned. Automatic replay is evidence of internal consistency, not independent semantic approval.",
        "",
        f"Selection: {report['selection_rule']}. Total: {len(tasks)} tasks.",
    ]
    for index, task in enumerate(tasks, 1):
        lines.extend(
            [
                "",
                f"## {index}. `{task['source_path']}` ({task['split']})",
                "",
                f"Source goal: `{json.dumps(task['source_goal_expression'])}`",
                "",
                "Compiled goal alternatives:",
                "",
                *[
                    f"- " + "; ".join(alternative)
                    for alternative in task["compiled_goal_alternatives"]
                ],
                "",
                "Review trace:",
                "",
                *[
                    f"{step}. `{action_id}`"
                    for step, action_id in enumerate(task["review_trace"], 1)
                ],
                "",
                "Reviewer checks:",
                "",
                "- [ ] Source goal is compiled faithfully.",
                "- [ ] Preconditions match the declared high-level abstraction.",
                "- [ ] Effects match the declared high-level abstraction.",
                "- [ ] The trace is plausible at that abstraction level.",
                "- [ ] Selective closed-world assumptions are acceptable.",
                "- Decision: approve / revise / reject",
                "- Reviewer and date:",
                "- Notes:",
            ]
        )
    args.markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"task_count": len(tasks), "splits": sorted(grouped)}, indent=2))


if __name__ == "__main__":
    main()
