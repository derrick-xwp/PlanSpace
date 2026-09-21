"""Re-open the 100 selected BDDL sources and audit translation support."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import median

from planspace.compatibility import audit_selected_sources


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("activity_root", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-goal-alternatives", type=int, default=10000)
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    audited = audit_selected_sources(
        args.activity_root,
        selection["selected_records"],
        max_goal_alternatives=args.max_goal_alternatives,
    )
    status_counts = Counter(record["translation_status"] for record in audited)
    alternative_counts = [
        record["goal_alternative_count"]
        for record in audited
        if record["goal_alternative_count"] is not None
    ]
    report = {
        "evidence_status": "structural_translation_audit_not_action_semantics_evidence",
        "audit_version": "planspace_compatibility_translation_v0.1",
        "screen_version": selection["screen_version"],
        "selected_count": len(audited),
        "translation_status_counts": dict(sorted(status_counts.items())),
        "goal_alternative_count_summary": {
            "min": min(alternative_counts) if alternative_counts else None,
            "median": median(alternative_counts) if alternative_counts else None,
            "max": max(alternative_counts) if alternative_counts else None,
        },
        "semantic_boundary": (
            "A translation pass verifies source consistency and finite goal compilation only; "
            "it does not provide or approve action semantics."
        ),
        "records": audited,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
