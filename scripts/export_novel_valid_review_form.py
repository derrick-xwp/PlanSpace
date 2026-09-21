#!/usr/bin/env python3
"""Export a frozen, human-editable form for outside-family plan cases."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDS = (
    "audit_id",
    "source_path",
    "source_sha256",
    "plan_json",
    "semantically_valid_at_declared_abstraction",
    "should_expand_constructed_family",
    "classification",
    "reviewer",
    "date",
    "notes",
)


def export_rows(packet: dict) -> list[dict[str, str]]:
    rows = []
    for case in packet["cases"]:
        rows.append(
            {
                "audit_id": case["audit_id"],
                "source_path": case["source_path"],
                "source_sha256": case["source_sha256"],
                "plan_json": json.dumps(case["plan"], separators=(",", ":")),
                "semantically_valid_at_declared_abstraction": "",
                "should_expand_constructed_family": "",
                "classification": "",
                "reviewer": "",
                "date": "",
                "notes": "",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    rows = export_rows(packet)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(args.output)


if __name__ == "__main__":
    main()
