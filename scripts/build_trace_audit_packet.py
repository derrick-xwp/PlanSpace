"""Build a 20-trace candidate packet for manual semantic review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import action_ids, execute_plan
from planspace.pilot_domains import (
    ACTION_DOMAIN_VERSION,
    installing_a_printer_problem,
    moving_boxes_to_storage_problem,
    opening_doors_problem,
    organizing_file_cabinet_problem,
    storing_food_problem,
)


ADAPTERS = {
    "installing_a_printer": installing_a_printer_problem,
    "opening_doors": opening_doors_problem,
    "moving_boxes_to_storage": moving_boxes_to_storage_problem,
    "organizing_file_cabinet": organizing_file_cabinet_problem,
    "storing_food": storing_food_problem,
}


def render_markdown(report: dict) -> str:
    lines = [
        "# Candidate Trace Audit Packet v0.1",
        "",
        f"Evidence status: `{report['evidence_status']}`.",
        "",
        report["review_policy"],
        "",
    ]
    for trace in report["traces"]:
        result = trace["execution_result"]
        lines.extend(
            [
                f"## {trace['trace_id']}",
                "",
                f"- Expected kind: `{trace['expected_kind']}`",
                f"- Executable: `{result['executable']}`",
                f"- Goal satisfied: `{result['goal_satisfied']}`",
                f"- Failure step: `{result['failure_step']}`",
                f"- Missing preconditions: `{', '.join(result['missing_preconditions']) or 'none'}`",
                "- Plan:",
                "",
            ]
        )
        lines.extend(f"  {index}. `{action_id}`" for index, action_id in enumerate(trace["plan"], 1))
        lines.extend(
            [
                "",
                "Review:",
                "",
                "- [ ] Action granularity is faithful.",
                "- [ ] Preconditions are faithful.",
                "- [ ] Effects are faithful.",
                "- [ ] Expected valid/invalid label is correct.",
                "- Reviewer and notes:",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture_root", type=Path)
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()

    traces = []
    task_summary = []
    for activity, adapter in ADAPTERS.items():
        source = parse_problem_file(args.fixture_root / f"{activity}_problem0.bddl")
        problem = adapter(source)
        actions = {action.action_id: action for action in problem.actions}
        metric_path = args.artifact_root / f"{activity}_v3_9_2_candidate_metrics.json"
        metrics = json.loads(metric_path.read_text(encoding="utf-8"))

        positive_plans = [family["plan"] for family in metrics["families"]]
        chosen_positive = [positive_plans[0]]
        if len(positive_plans) > 1:
            chosen_positive.append(positive_plans[-1])
        negative_needed = 4 - len(chosen_positive)
        chosen = [("valid", plan) for plan in chosen_positive]
        chosen += [
            ("invalid", record["plan"])
            for record in metrics["structured_negatives"][:negative_needed]
        ]

        for local_index, (kind, plan_ids) in enumerate(chosen, 1):
            plan = tuple(actions[action_id] for action_id in plan_ids)
            execution = execute_plan(problem, plan)
            traces.append(
                {
                    "trace_id": f"{activity}-{local_index:02d}",
                    "activity": activity,
                    "expected_kind": kind,
                    "plan": list(action_ids(plan)),
                    "action_details": [
                        {
                            "action_id": action.action_id,
                            "operator": action.operator,
                            "preconditions": sorted(map(str, action.preconditions)),
                            "add_effects": sorted(map(str, action.add_effects)),
                            "delete_effects": sorted(map(str, action.delete_effects)),
                        }
                        for action in plan
                    ],
                    "execution_result": {
                        "executable": execution.executable,
                        "goal_satisfied": execution.goal_satisfied,
                        "valid": execution.valid,
                        "failure_step": execution.failure_step,
                        "failed_action_id": execution.failed_action_id,
                        "missing_preconditions": sorted(
                            map(str, execution.missing_preconditions)
                        ),
                    },
                    "manual_review": {
                        "status": "pending_independent_review",
                        "action_granularity_faithful": None,
                        "preconditions_faithful": None,
                        "effects_faithful": None,
                        "expected_label_correct": None,
                        "reviewer_notes": None,
                    },
                }
            )
        task_summary.append(
            {
                "activity": activity,
                "trace_count": len(chosen),
                "valid_trace_count": len(chosen_positive),
                "invalid_trace_count": negative_needed,
            }
        )

    if len(traces) != 20:
        raise RuntimeError(f"expected 20 traces, generated {len(traces)}")
    report = {
        "evidence_status": "candidate_trace_packet_pending_independent_semantic_review",
        "action_domain_version": ACTION_DOMAIN_VERSION,
        "trace_count": len(traces),
        "review_policy": (
            "An independent reviewer must inspect every action abstraction and trace label. "
            "Automated replay proves consistency with candidate code, not real-world faithfulness."
        ),
        "task_summary": task_summary,
        "traces": traces,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output is not None:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "traces"}, indent=2))


if __name__ == "__main__":
    main()
