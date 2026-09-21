#!/usr/bin/env python3
"""Compare frozen semantic-review packets across action-domain versions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def identifier(task: dict) -> str:
    return f"{task['split']}::{task['source_path']}"


def action_semantics(task: dict) -> dict[str, dict]:
    return {
        action["action_id"]: {
            key: action.get(key, [])
            for key in ("preconditions", "add_effects", "delete_effects", "constraints")
        }
        for action in task["actions"]
    }


def analyze(old: dict, new: dict) -> dict:
    old_tasks = {identifier(task): task for task in old["tasks"]}
    new_tasks = {identifier(task): task for task in new["tasks"]}
    if set(old_tasks) != set(new_tasks):
        raise ValueError("packet task sets differ")
    rows = []
    for task_id in sorted(old_tasks):
        left, right = old_tasks[task_id], new_tasks[task_id]
        left_actions, right_actions = action_semantics(left), action_semantics(right)
        common = set(left_actions) & set(right_actions)
        changed_preconditions = sorted(
            item for item in common
            if left_actions[item]["preconditions"] != right_actions[item]["preconditions"]
        )
        changed_effects = sorted(
            item for item in common
            if any(
                left_actions[item][field] != right_actions[item][field]
                for field in ("add_effects", "delete_effects")
            )
        )
        added_constraints = sorted(
            item for item in common
            if left_actions[item]["constraints"] != right_actions[item]["constraints"]
        )
        row = {
            "task_id": task_id,
            "source_overlay": right.get("source_overlay"),
            "goal_changed": left["compiled_goal_alternatives"] != right["compiled_goal_alternatives"],
            "initial_state_changed": left["compiled_initial_state"] != right["compiled_initial_state"],
            "added_action_ids": sorted(set(right_actions) - set(left_actions)),
            "removed_action_ids": sorted(set(left_actions) - set(right_actions)),
            "changed_precondition_action_ids": changed_preconditions,
            "changed_effect_action_ids": changed_effects,
            "constraint_changed_action_ids": added_constraints,
            "reference_trace_changed": left["review_trace"] != right["review_trace"],
            "old_trace_length": len(left["review_trace"]),
            "new_trace_length": len(right["review_trace"]),
        }
        row["substantive_semantic_change"] = any(
            (
                row["goal_changed"],
                row["initial_state_changed"],
                row["added_action_ids"],
                row["removed_action_ids"],
                row["changed_precondition_action_ids"],
                row["changed_effect_action_ids"],
                row["reference_trace_changed"],
            )
        )
        # v0.4 renders an explicit constraints field for every catalog action,
        # including actions whose constraint list is empty.
        row["model_prompt_changed"] = True
        rows.append(row)
    substantive = sum(row["substantive_semantic_change"] for row in rows)
    prompt = sum(row["model_prompt_changed"] for row in rows)
    report = {
        "analysis_version": "planspace-semantic-v04-impact-v0.1",
        "old_packet_version": old["packet_version"],
        "new_packet_version": new["packet_version"],
        "task_count": len(rows),
        "substantively_changed_task_count": substantive,
        "substantively_changed_task_fraction": substantive / len(rows),
        "model_prompt_changed_task_count": prompt,
        "model_prompt_changed_task_fraction": prompt / len(rows),
        "full_rerun_required": prompt > 0,
        "full_rerun_reason": (
            "The action catalog shown to models changed. Confirmatory comparisons require "
            "all models to receive one frozen protocol rather than mixing v0.3 and v0.4 prompts."
        ),
        "tasks": rows,
    }
    return report


def render(report: dict) -> str:
    lines = [
        "# Semantic v0.4 impact analysis",
        "",
        f"Tasks: {report['task_count']}.",
        f"Substantive semantic changes: {report['substantively_changed_task_count']} "
        f"({report['substantively_changed_task_fraction']:.1%}).",
        f"Model prompts changed: {report['model_prompt_changed_task_count']} "
        f"({report['model_prompt_changed_task_fraction']:.1%}).",
        "",
        f"Full rerun required: **{'yes' if report['full_rerun_required'] else 'no'}**.",
        "",
        report["full_rerun_reason"],
        "",
        "| Task | Goal | Initial | Action IDs | Preconditions | Constraints | Trace |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["tasks"]:
        lines.append(
            "| {task} | {goal} | {initial} | {ids} | {pre} | {guard} | {trace} |".format(
                task=row["task_id"],
                goal="yes" if row["goal_changed"] else "no",
                initial="yes" if row["initial_state_changed"] else "no",
                ids=len(row["added_action_ids"]) + len(row["removed_action_ids"]),
                pre=len(row["changed_precondition_action_ids"]),
                guard=len(row["constraint_changed_action_ids"]),
                trace="yes" if row["reference_trace_changed"] else "no",
            )
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("old_packet", type=Path)
    parser.add_argument("new_packet", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(
        json.loads(args.old_packet.read_text(encoding="utf-8")),
        json.loads(args.new_packet.read_text(encoding="utf-8")),
    )
    args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render(report), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "tasks"}, indent=2))


if __name__ == "__main__":
    main()
