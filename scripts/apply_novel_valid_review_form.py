#!/usr/bin/env python3
"""Validate a completed outside-family review form against its frozen packet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


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
    expected = {case["audit_id"]: case for case in packet["cases"]}
    observed = {row.get("audit_id", ""): row for row in rows}
    if len(observed) != len(rows):
        raise ValueError("completed form contains duplicate audit IDs")
    if set(observed) != set(expected):
        raise ValueError("completed form audit IDs differ from the frozen packet")
    reviewers = {row.get("reviewer", "").strip() for row in rows}
    if len(reviewers) != 1 or not next(iter(reviewers)):
        raise ValueError("one non-empty reviewer identity is required for every row")

    output = json.loads(json.dumps(packet))
    allowed = set(packet["allowed_classifications"])
    for case in output["cases"]:
        identifier = case["audit_id"]
        row = observed[identifier]
        expected_plan = json.dumps(case["plan"], separators=(",", ":"))
        if (
            row.get("source_path") != case["source_path"]
            or row.get("source_sha256") != case["source_sha256"]
            or row.get("plan_json") != expected_plan
        ):
            raise ValueError(f"frozen metadata mismatch for {identifier}")
        classification = row.get("classification", "").strip()
        if classification not in allowed:
            raise ValueError(f"{identifier} has invalid classification {classification!r}")
        if not row.get("date", "").strip():
            raise ValueError(f"{identifier} lacks a review date")
        case["review"] = {
            "semantically_valid_at_declared_abstraction": parse_bool(
                row.get("semantically_valid_at_declared_abstraction", ""),
                identifier=identifier,
                field="semantically_valid_at_declared_abstraction",
            ),
            "should_expand_constructed_family": parse_bool(
                row.get("should_expand_constructed_family", ""),
                identifier=identifier,
                field="should_expand_constructed_family",
            ),
            "classification": classification,
            "reviewer": row["reviewer"].strip(),
            "date": row["date"].strip(),
            "notes": row.get("notes", "").strip(),
        }
    output["evidence_status"] = "completed_human_outside_family_audit"
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
