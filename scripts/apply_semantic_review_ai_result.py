#!/usr/bin/env python3
"""Validate a Codex CLI semantic audit and attach it to a frozen packet.

The output status is intentionally distinct from human-review evidence, so it
cannot satisfy the release gate for independent human semantic validation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.analyze_semantic_review_agreement import BOOLEAN_FIELDS, DECISIONS, task_id


def apply_result(packet: dict, result: dict) -> dict:
    if result.get("reviewer_kind") != "codex_cli_ai":
        raise ValueError("result reviewer_kind must be codex_cli_ai")
    reviewer = result.get("reviewer", "").strip()
    date = result.get("date", "").strip()
    if not reviewer or not date:
        raise ValueError("AI reviewer identity and date are required")

    rows = result.get("rows")
    if not isinstance(rows, list):
        raise ValueError("result rows must be a list")
    # The packet's stable identity is (split, source_path).  Task IDs in
    # natural-language review forms are useful labels, but older packets did
    # not expose the internal ``split::source_path`` identifier to reviewers.
    # Match only on the immutable metadata and retain the supplied label.
    expected = {(task["split"], task["source_path"]): task for task in packet["tasks"]}
    observed = {(row.get("split"), row.get("source_path")): row for row in rows}
    if len(observed) != len(rows):
        raise ValueError("AI result contains duplicate split/source-path pairs")
    if set(observed) != set(expected):
        raise ValueError("frozen metadata mismatch in AI result split/source-path pairs")

    output = json.loads(json.dumps(packet))
    for task in output["tasks"]:
        identifier = task_id(task)
        row = observed[(task["split"], task["source_path"])]
        for field in BOOLEAN_FIELDS:
            if not isinstance(row.get(field), bool):
                raise ValueError(f"{identifier} lacks boolean {field}")
        if row.get("decision") not in DECISIONS:
            raise ValueError(f"{identifier} has invalid decision {row.get('decision')!r}")
        task["review"] = {
            **{field: row[field] for field in BOOLEAN_FIELDS},
            "decision": row["decision"],
            "reviewer": reviewer,
            "reviewer_kind": "codex_cli_ai",
            "date": date,
            "notes": row.get("notes", "").strip(),
        }
    output["evidence_status"] = "completed_independent_codex_cli_ai_review"
    output["evidence_boundary"] = (
        "AI-assisted semantic audit only; this is not independent human validation "
        "and cannot satisfy the human-review release gate."
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    completed = apply_result(packet, result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(completed, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
