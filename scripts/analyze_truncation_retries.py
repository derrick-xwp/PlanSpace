#!/usr/bin/env python3
"""Compare 256-token runs with 512-token retries on capped tasks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def rates(tasks: list[dict[str, object]]) -> dict[str, float | int | None]:
    samples = [sample for task in tasks for sample in task["samples"]]
    if not samples:
        return {"sample_count": 0, "parse": None, "goal": None, "exact": None}
    return {
        "sample_count": len(samples),
        "parse": sum(sample["parse_error"] is None for sample in samples) / len(samples),
        "goal": sum(
            bool(sample["execution"] and sample["execution"]["valid"])
            for sample in samples
        )
        / len(samples),
        "exact": sum(sample["exact_match"] for sample in samples) / len(samples),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs", nargs="+", help="BASE_JSON:RETRY_JSON")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--table-output", required=True, type=Path)
    args = parser.parse_args()

    rows = []
    for pair in args.pairs:
        base_path, retry_path = map(Path, pair.split(":", 1))
        base = json.loads(base_path.read_text(encoding="utf-8"))
        retry = json.loads(retry_path.read_text(encoding="utf-8"))
        retry_paths = {task["source_path"] for task in retry["tasks"]}
        base_tasks = [task for task in base["tasks"] if task["source_path"] in retry_paths]
        if len(base_tasks) != len(retry["tasks"]):
            raise ValueError(f"base/retry task mismatch for {base['model_id']}")
        base_rates = rates(base_tasks)
        retry_rates = rates(retry["tasks"])
        rows.append(
            {
                "model_id": base["model_id"],
                "task_count": len(base_tasks),
                "base_max_new_tokens": base["decoding"]["max_new_tokens"],
                "retry_max_new_tokens": retry["decoding"]["max_new_tokens"],
                "base": base_rates,
                "retry": retry_rates,
                "goal_valid_delta": (
                    retry_rates["goal"] - base_rates["goal"]
                    if retry_rates["goal"] is not None
                    else None
                ),
            }
        )
    report = {
        "evidence_status": "candidate_budget_sensitivity_pending_semantic_review",
        "analysis_version": "planspace-truncation-retry-v0.1",
        "models": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.table_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Output-budget sensitivity on capped tasks",
        "",
        "Each 512-token run retries only tasks with at least one capped parse failure in the corresponding 256-token matrix.",
        "",
        "| Model | Tasks | Parse@256 | Goal@256 | Parse@512 | Goal@512 | Goal delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    def fmt(value):
        return "--" if value is None else f"{value:.2%}"

    def fmt_signed(value):
        return "--" if value is None else f"{value:+.2%}"

    for row in rows:
        lines.append(
            f"| {row['model_id']} | {row['task_count']} | {fmt(row['base']['parse'])} | "
            f"{fmt(row['base']['goal'])} | {fmt(row['retry']['parse'])} | "
            f"{fmt(row['retry']['goal'])} | {fmt_signed(row['goal_valid_delta'])} |"
        )
    args.table_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
