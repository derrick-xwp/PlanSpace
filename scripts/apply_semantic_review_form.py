#!/usr/bin/env python3
"""Validate a completed CSV form and apply it to a frozen review packet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scripts.analyze_semantic_review_agreement import BOOLEAN_FIELDS, DECISIONS, task_id


TRUE = {"true", "yes", "y", "1"}
FALSE = {"false", "no", "n", "0"}


def parse_bool(value: str, *, identifier: str, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE:
        return True
    if normalized in FALSE:
        return False
    raise ValueError(f"{identifier} has invalid {field}: {value!r}")


def apply_form(packet: dict, rows: list[dict[str, str]]) -> dict:
    expected = {task_id(task): task for task in packet["tasks"]}
    observed = {row["task_id"]: row for row in rows}
    if len(observed) != len(rows):
        raise ValueError("completed form contains duplicate task IDs")
    if set(observed) != set(expected):
        raise ValueError("completed form task IDs differ from the frozen packet")
    reviewer_names = {row.get("reviewer", "").strip() for row in rows}
    if len(reviewer_names) != 1 or not next(iter(reviewer_names)):
        raise ValueError("one non-empty reviewer identity is required for every row")

    output = json.loads(json.dumps(packet))
    for task in output["tasks"]:
        identifier = task_id(task)
        row = observed[identifier]
        if row.get("source_path") != task["source_path"] or row.get("split") != task["split"]:
            raise ValueError(f"frozen metadata mismatch for {identifier}")
        review = task["review"]
        for field in BOOLEAN_FIELDS:
            review[field] = parse_bool(row.get(field, ""), identifier=identifier, field=field)
        decision = row.get("decision", "").strip().lower()
        if decision not in DECISIONS:
            raise ValueError(f"{identifier} has invalid decision {decision!r}")
        if not row.get("date", "").strip():
            raise ValueError(f"{identifier} lacks a review date")
        review.update(
            {
                "decision": decision,
                "reviewer": row["reviewer"].strip(),
                "date": row["date"].strip(),
                "notes": row.get("notes", "").strip(),
            }
        )
    output["evidence_status"] = "completed_independent_review"
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("completed_form", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    with args.completed_form.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    completed = apply_form(packet, rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(completed, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
