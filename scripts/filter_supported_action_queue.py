#!/usr/bin/env python3
"""Filter a reviewed action queue to tasks supported by a frozen domain audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SUPPORTED_STATUS = "candidate_supported_all_goal_alternatives"


def build_supported_queue(queue: dict, audit: dict) -> dict:
    audit_by_path = {row["source_path"]: row for row in audit["tasks"]}
    queue_paths = [row["source_path"] for row in queue["records"]]
    if len(queue_paths) != len(set(queue_paths)):
        raise ValueError("queue contains duplicate source paths")
    if set(queue_paths) != set(audit_by_path):
        raise ValueError("queue and domain audit task sets differ")
    records = [
        row
        for row in queue["records"]
        if audit_by_path[row["source_path"]]["status"] == SUPPORTED_STATUS
    ]
    excluded = [
        {
            "source_path": row["source_path"],
            "status": audit_by_path[row["source_path"]]["status"],
            "errors": audit_by_path[row["source_path"]].get("errors", []),
        }
        for row in queue["records"]
        if audit_by_path[row["source_path"]]["status"] != SUPPORTED_STATUS
    ]
    return {
        **{key: value for key, value in queue.items() if key != "records"},
        "evidence_status": "domain_audit_filtered_supported_expanded_queue",
        "queue_version": "planspace_action_semantics_supported_expanded_v0.1",
        "source_queue_version": queue["queue_version"],
        "domain_audit_version": audit["audit_version"],
        "selected_count": len(records),
        "excluded_count": len(excluded),
        "excluded": excluded,
        "semantic_boundary": (
            "Every retained task is candidate-supported for all compiled goal alternatives "
            "by the recorded frozen generic-domain audit. This is executable symbolic "
            "coverage, not independent human or simulator validation."
        ),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("domain_audit", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    audit = json.loads(args.domain_audit.read_text(encoding="utf-8"))
    result = build_supported_queue(queue, audit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"retained {result['selected_count']} tasks; excluded {result['excluded_count']}"
    )


if __name__ == "__main__":
    main()
