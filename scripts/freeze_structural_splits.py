#!/usr/bin/env python3
"""Freeze one core and four disjoint structural stress-test splits."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


SPLIT_VERSION = "planspace-structural-splits-v0.1"


def assign(record: dict[str, object]) -> str:
    """Assign by fixed priority so all splits are disjoint."""

    if record["unique_plan_representative_count"] > 1:
        return "ood_goal_choice"
    if record["plan_length_max"] >= 7:
        return "ood_long_horizon"
    if len(record["operator_vocabulary"]) >= 3:
        return "ood_operator_composition"
    if record["topological_orders_checked"] > record["unique_plan_representative_count"]:
        return "ood_commutation"
    return "iid_core"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("domain_audit", type=Path)
    parser.add_argument("--queue", type=Path)
    parser.add_argument("--expected-count", type=int, default=100)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    audit = json.loads(args.domain_audit.read_text(encoding="utf-8"))
    audit_tasks = audit["tasks"]
    if args.queue:
        queue = json.loads(args.queue.read_text(encoding="utf-8"))
        queue_paths = [row["source_path"] for row in queue["records"]]
        if len(queue_paths) != len(set(queue_paths)):
            raise ValueError("queue contains duplicate source paths")
        audit_by_path = {row["source_path"]: row for row in audit_tasks}
        if not set(queue_paths) <= set(audit_by_path):
            raise ValueError("queue contains tasks absent from domain audit")
        audit_tasks = [audit_by_path[path] for path in queue_paths]
    records = [
        {
            "source_path": record["source_path"],
            "source_sha256": record["source_sha256"],
            "split": assign(record),
        }
        for record in audit_tasks
    ]
    counts = Counter(record["split"] for record in records)
    report = {
        "evidence_status": "frozen_before_complete_model_results_pending_semantic_review",
        "split_version": SPLIT_VERSION,
        "source_audit_version": audit["audit_version"],
        "assignment_priority": [
            "ood_goal_choice: more than one validated goal-plan representative",
            "ood_long_horizon: maximum validated reference length at least 7",
            "ood_operator_composition: at least 3 operator types",
            "ood_commutation: more validated topological orders than representatives",
            "iid_core: all remaining tasks",
        ],
        "counts": dict(sorted(counts.items())),
        "records": records,
    }
    if len(records) != args.expected_count or set(counts) != {
        "iid_core",
        "ood_goal_choice",
        "ood_long_horizon",
        "ood_operator_composition",
        "ood_commutation",
    }:
        raise ValueError(
            f"expected {args.expected_count} tasks and all five structural splits"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], indent=2))


if __name__ == "__main__":
    main()
