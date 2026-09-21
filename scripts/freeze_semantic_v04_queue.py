#!/usr/bin/env python3
"""Freeze the v0.4 queue with explicit, checksummed source overlays."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.translation import goal_alternatives, goal_quantifier_diagnostics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("old_queue", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("source_overlay", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    queue = json.loads(args.old_queue.read_text(encoding="utf-8"))
    output = json.loads(json.dumps(queue))
    repairs = []
    for record in output["records"]:
        relative = Path(record["source_path"])
        original = args.source_root / relative
        overlay = args.source_overlay / relative
        selected = overlay if overlay.exists() else original
        original_hash = sha256(original.read_bytes()).hexdigest()
        if original_hash != record["source_sha256"]:
            raise ValueError(f"original source drift for {relative}")
        source = parse_problem_file(selected)
        alternatives = goal_alternatives(source)
        selected_hash = sha256(selected.read_bytes()).hexdigest()
        record["original_source_sha256"] = original_hash
        record["source_sha256"] = selected_hash
        record["source_overlay"] = str(relative) if overlay.exists() else None
        record["goal_alternative_count"] = len(alternatives)
        record["source_goal_diagnostics"] = list(goal_quantifier_diagnostics(source))
        if overlay.exists():
            repairs.append(
                {
                    "source_path": str(relative),
                    "original_source_sha256": original_hash,
                    "repaired_source_sha256": selected_hash,
                }
            )
    output.update(
        {
            "evidence_status": "semantic_v04_queue_frozen_pending_ai_reaudit",
            "queue_version": "planspace_action_semantics_review_v0.4",
            "generic_domain_version": "planspace_generic_household_v0.4-candidate",
            "source_repairs": repairs,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"task_count": len(output["records"]), "source_repairs": repairs}, indent=2))


if __name__ == "__main__":
    main()
