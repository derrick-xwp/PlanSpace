#!/usr/bin/env python3
"""Export a compact CSV form from the frozen semantic review packet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scripts.analyze_semantic_review_agreement import REVIEW_FIELDS, task_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    fields = ["task_id", "source_path", "split", *REVIEW_FIELDS, "reviewer", "date", "notes"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for task in packet["tasks"]:
            writer.writerow(
                {
                    "task_id": task_id(task),
                    "source_path": task["source_path"],
                    "split": task["split"],
                }
            )
    print(args.output)


if __name__ == "__main__":
    main()
