#!/usr/bin/env python3
"""Build a deduplicated review packet for goal-valid plans outside known DAGs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


CLASSIFICATIONS = (
    "valid_novel_or_nonminimal_plan",
    "constructed_family_coverage_miss",
    "action_semantics_or_evaluator_issue",
    "not_semantically_valid",
)


def build_packet(paths: list[Path]) -> dict:
    grouped: dict[tuple[str, tuple[str, ...]], dict] = {}
    total_occurrences = 0
    model_counts = defaultdict(int)
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        model_id = report["model_id"]
        for task in report["tasks"]:
            for sample in task["samples"]:
                execution = sample.get("execution") or {}
                if not execution.get("valid") or sample.get("partial_order_match") is not False:
                    continue
                total_occurrences += 1
                model_counts[model_id] += 1
                plan = tuple(sample["parsed_plan"])
                key = (task["source_path"], plan)
                if key not in grouped:
                    grouped[key] = {
                        "audit_id": None,
                        "source_path": task["source_path"],
                        "source_sha256": task["source_sha256"],
                        "plan": list(plan),
                        "reference_plan": task["reference_plan"],
                        "reference_plan_dags": task["reference_plan_dags"],
                        "execution_result": execution,
                        "occurrences": [],
                        "review": {
                            "classification": None,
                            "semantically_valid_at_declared_abstraction": None,
                            "should_expand_constructed_family": None,
                            "reviewer": None,
                            "date": None,
                            "notes": None,
                        },
                    }
                grouped[key]["occurrences"].append(
                    {
                        "model_id": model_id,
                        "model_revision": report["model_revision"],
                        "sample_index": sample["sample_index"],
                        "seed": sample["seed"],
                    }
                )

    cases = sorted(grouped.values(), key=lambda x: (x["source_path"], x["plan"]))
    for index, case in enumerate(cases, 1):
        case["audit_id"] = f"novel-valid-{index:03d}"
    return {
        "evidence_status": "pending_independent_novel_valid_review",
        "packet_version": "planspace-novel-valid-audit-v0.1",
        "source_files": [path.name for path in paths],
        "selection_rule": (
            "Every sample with deterministic goal validity true and constructed "
            "partial-order-family membership false; exact duplicate task-plan pairs are merged."
        ),
        "total_occurrence_count": total_occurrences,
        "unique_case_count": len(cases),
        "model_occurrence_counts": dict(sorted(model_counts.items())),
        "allowed_classifications": list(CLASSIFICATIONS),
        "boundary": (
            "Goal validity is relative to the declared high-level transition model. Human review "
            "must distinguish legitimate nonminimal behavior from family coverage or semantic errors."
        ),
        "cases": cases,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# PlanSpace novel-valid audit packet v0.1",
        "",
        f"Evidence status: `{report['evidence_status']}`.",
        "",
        report["selection_rule"],
        "",
        f"Occurrences: {report['total_occurrence_count']}; unique task-plan cases: {report['unique_case_count']}.",
        "",
        "Allowed classifications:",
        "",
        *[f"- `{item}`" for item in report["allowed_classifications"]],
    ]
    for case in report["cases"]:
        goals = sorted(
            {
                "; ".join(goal)
                for dag in case["reference_plan_dags"]
                for goal in dag.get("goals", [])
            }
        )
        lines.extend(
            [
                "",
                f"## {case['audit_id']}: `{case['source_path']}`",
                "",
                f"Observed {len(case['occurrences'])} time(s).",
                "",
                "Goal alternatives represented by constructed families:",
                "",
                *[f"- `{goal}`" for goal in goals],
                "",
                "Reference plan:",
                "",
                *[f"{i}. `{action}`" for i, action in enumerate(case["reference_plan"], 1)],
                "",
                "Candidate goal-valid plan outside known families:",
                "",
                *[f"{i}. `{action}`" for i, action in enumerate(case["plan"], 1)],
                "",
                "Review:",
                "",
                "- Classification:",
                "- Semantically valid at the declared abstraction: yes / no",
                "- Should the constructed family be expanded: yes / no",
                "- Reviewer and date:",
                "- Notes:",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    args = parser.parse_args()
    report = build_packet(args.inputs)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
