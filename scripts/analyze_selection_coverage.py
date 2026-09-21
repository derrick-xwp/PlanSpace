#!/usr/bin/env python3
"""Quantify selection flow and distribution shift into the frozen task queue."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median


def signature(record: dict) -> str:
    return "+".join(sorted(record["goal_predicates"]))


def summarize(records: list[dict]) -> dict:
    object_counts = [record["object_count"] for record in records]
    signatures = Counter(signature(record) for record in records)
    goal_predicates = Counter(
        predicate for record in records for predicate in set(record["goal_predicates"])
    )
    return {
        "count": len(records),
        "object_count": {
            "min": min(object_counts) if object_counts else None,
            "median": median(object_counts) if object_counts else None,
            "mean": mean(object_counts) if object_counts else None,
            "max": max(object_counts) if object_counts else None,
        },
        "implicit_goal_conjunction_count": sum(
            bool(record["implicit_goal_conjunction"]) for record in records
        ),
        "goal_signature_counts": dict(sorted(signatures.items())),
        "goal_predicate_task_counts": dict(sorted(goal_predicates.items())),
    }


def analyze(source: dict, screen: dict, translation: dict, queue: dict) -> dict:
    source_records = source["records"]
    supported = set(screen["rubric"]["supported_goal_predicates"])
    max_objects = screen["rubric"]["max_object_count"]
    eligible = [
        record
        for record in source_records
        if record["object_count"] <= max_objects
        and set(record["goal_predicates"]) <= supported
    ]
    if len(eligible) != screen["eligible_count"]:
        raise ValueError("recomputed structural eligibility does not match frozen screen")

    buffer_paths = {record["source_path"] for record in screen["selected_records"]}
    buffer_records = [record for record in source_records if record["source_path"] in buffer_paths]
    if len(buffer_records) != screen["selected_count"]:
        raise ValueError("buffer selection path mismatch")

    pass_paths = {
        record["source_path"]
        for record in translation["records"]
        if record["translation_status"] == "pass"
    }
    translation_pass = [record for record in source_records if record["source_path"] in pass_paths]
    queue_paths = {record["source_path"] for record in queue["records"]}
    final_records = [record for record in source_records if record["source_path"] in queue_paths]
    if len(final_records) != queue["selected_count"]:
        raise ValueError("final queue path mismatch")
    if not queue_paths <= pass_paths:
        raise ValueError("final queue contains a task without a translation pass")

    structural_exclusion = Counter()
    for record in source_records:
        unsupported = sorted(set(record["goal_predicates"]) - supported)
        too_many = record["object_count"] > max_objects
        if not unsupported and not too_many:
            continue
        if unsupported and too_many:
            key = "unsupported_goal_predicate_and_object_count"
        elif unsupported:
            key = "unsupported_goal_predicate"
        else:
            key = "object_count_above_limit"
        structural_exclusion[key] += 1

    translation_failures = Counter(
        record.get("error") or "unspecified_translation_failure"
        for record in translation["records"]
        if record["translation_status"] != "pass"
    )
    stages = {
        "all_parsed_sources": summarize(source_records),
        "structurally_eligible": summarize(eligible),
        "audited_buffer": summarize(buffer_records),
        "finite_translation_pass": summarize(translation_pass),
        "frozen_final_queue": summarize(final_records),
    }
    return {
        "evidence_status": "descriptive_selection_coverage_audit",
        "analysis_version": "planspace-selection-coverage-v0.1",
        "funnel": [
            {"stage": name, "count": summary["count"]}
            for name, summary in stages.items()
        ],
        "stages": stages,
        "structural_exclusion_reason_counts": dict(sorted(structural_exclusion.items())),
        "translation_failure_counts": dict(sorted(translation_failures.items())),
        "translation_pass_not_selected_count": len(pass_paths - queue_paths),
        "boundary": (
            "The final queue is a deterministic compatibility-filtered subset, not an unbiased "
            "sample of all BEHAVIOR-1K activities. Distribution summaries are descriptive only."
        ),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# PlanSpace task-selection coverage audit v0.1",
        "",
        f"Evidence status: `{report['evidence_status']}`.",
        "",
        "## Selection funnel",
        "",
        "| Stage | Tasks |",
        "| --- | ---: |",
        *[f"| {row['stage']} | {row['count']} |" for row in report["funnel"]],
        "",
        "## Object-count shift",
        "",
        "| Stage | Min | Median | Mean | Max |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, stage in report["stages"].items():
        values = stage["object_count"]
        lines.append(
            f"| {name} | {values['min']} | {values['median']:.1f} | "
            f"{values['mean']:.2f} | {values['max']} |"
        )
    lines.extend(
        [
            "",
            "## Structural exclusion reasons",
            "",
            *[f"- `{key}`: {value}" for key, value in report["structural_exclusion_reason_counts"].items()],
            "",
            "## Translation failures in the 120-task audit buffer",
            "",
            *[f"- `{key}`: {value}" for key, value in report["translation_failure_counts"].items()],
            "",
            "## Interpretation boundary",
            "",
            report["boundary"],
            "",
            "Full per-stage goal-predicate and signature counts are available in the JSON artifact.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_audit", type=Path)
    parser.add_argument("buffer_screen", type=Path)
    parser.add_argument("translation_audit", type=Path)
    parser.add_argument("final_queue", type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    args = parser.parse_args()
    inputs = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (
            args.source_audit,
            args.buffer_screen,
            args.translation_audit,
            args.final_queue,
        )
    ]
    report = analyze(*inputs)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"funnel": report["funnel"], "boundary": report["boundary"]}, indent=2))


if __name__ == "__main__":
    main()
