#!/usr/bin/env python3
"""Export a blank adjudication form for frozen reviewer disagreements."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDS = (
    "task_id",
    "field",
    "reviewer_a_value",
    "reviewer_b_value",
    "adjudicated_value",
    "adjudicator",
    "date",
    "rationale",
)


def display(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def export(report: dict, path: Path) -> None:
    rows = []
    for item in report["disagreements"]:
        rows.append(
            {
                "task_id": item["task_id"],
                "field": item["field"],
                "reviewer_a_value": display(item["reviewer_a"]),
                "reviewer_b_value": display(item["reviewer_b"]),
                "adjudicated_value": "",
                "adjudicator": "",
                "date": "",
                "rationale": "",
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("agreement", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = json.loads(args.agreement.read_text(encoding="utf-8"))
    export(report, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
