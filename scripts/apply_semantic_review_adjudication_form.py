#!/usr/bin/env python3
"""Validate and freeze adjudication without altering independent labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from scripts.analyze_semantic_review_agreement import BOOLEAN_FIELDS, DECISIONS


TRUE = {"true", "yes", "y", "1"}
FALSE = {"false", "no", "n", "0"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def parse_value(field: str, value: str, identifier: str) -> object:
    normalized = value.strip().lower()
    if field in BOOLEAN_FIELDS:
        if normalized in TRUE:
            return True
        if normalized in FALSE:
            return False
        raise ValueError(f"{identifier} has invalid Boolean adjudication {value!r}")
    if field == "decision" and normalized in DECISIONS:
        return normalized
    raise ValueError(f"{identifier} has invalid decision adjudication {value!r}")


def apply(report: dict, rows: list[dict[str, str]], agreement_sha256: str) -> dict:
    expected = {
        (item["task_id"], item["field"]): item for item in report["disagreements"]
    }
    observed = {(row.get("task_id", ""), row.get("field", "")): row for row in rows}
    if len(observed) != len(rows):
        raise ValueError("adjudication form contains duplicate task-field rows")
    if set(observed) != set(expected):
        raise ValueError("adjudication rows differ from frozen disagreements")

    adjudicators = {row.get("adjudicator", "").strip() for row in rows}
    if rows and (len(adjudicators) != 1 or not next(iter(adjudicators))):
        raise ValueError("one stable adjudicator identity is required")

    records = []
    for key in sorted(expected):
        item = expected[key]
        row = observed[key]
        identifier = f"{key[0]}::{key[1]}"
        if (
            row.get("reviewer_a_value", "").strip().lower()
            != display(item["reviewer_a"]).lower()
            or row.get("reviewer_b_value", "").strip().lower()
            != display(item["reviewer_b"]).lower()
        ):
            raise ValueError(f"frozen reviewer labels changed for {identifier}")
        if not row.get("date", "").strip() or not row.get("rationale", "").strip():
            raise ValueError(f"{identifier} lacks date or rationale")
        records.append(
            {
                "task_id": key[0],
                "field": key[1],
                "reviewer_a": item["reviewer_a"],
                "reviewer_b": item["reviewer_b"],
                "adjudicated_value": parse_value(
                    key[1], row.get("adjudicated_value", ""), identifier
                ),
                "adjudicator": row["adjudicator"].strip(),
                "date": row["date"].strip(),
                "rationale": row["rationale"].strip(),
            }
        )
    return {
        "evidence_status": "completed_semantic_review_adjudication",
        "agreement_sha256": agreement_sha256,
        "record_count": len(records),
        "records": records,
        "boundary": (
            "Adjudication preserves the independent labels and resolves only their "
            "interpretation. Negative final judgments require benchmark revision."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("agreement", type=Path)
    parser.add_argument("completed_form", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = json.loads(args.agreement.read_text(encoding="utf-8"))
    with args.completed_form.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = apply(report, rows, digest(args.agreement))
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
