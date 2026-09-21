"""Select a deterministic 100-instance structural compatibility audit set."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from planspace.compatibility import (
    DEFAULT_SUPPORTED_GOAL_PREDICATES,
    select_stratified_records,
)


def _stable_counts(counter: Counter[tuple[str, ...]]) -> dict[str, int]:
    return {
        "+".join(signature): count
        for signature, count in sorted(counter.items(), key=lambda item: item[0])
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_audit", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-count", type=int, default=100)
    parser.add_argument("--max-object-count", type=int, default=20)
    parser.add_argument("--seed", default="planspace-compatibility-v0.1")
    args = parser.parse_args()

    source = json.loads(args.source_audit.read_text(encoding="utf-8"))
    selected, eligible_count = select_stratified_records(
        source["records"],
        target_count=args.target_count,
        seed=args.seed,
        max_object_count=args.max_object_count,
    )
    signatures = Counter(tuple(record["goal_predicates"]) for record in selected)
    report = {
        "evidence_status": "structural_screen_not_semantic_compatibility_evidence",
        "screen_version": "planspace_compatibility_v0.1",
        "source_activity_root": source["activity_root"],
        "source_problem_file_count": source["problem_file_count"],
        "rubric": {
            "parsed_source_required": True,
            "supported_goal_predicates": sorted(DEFAULT_SUPPORTED_GOAL_PREDICATES),
            "max_object_count": args.max_object_count,
            "selection": "deterministic round-robin over goal-predicate signatures",
            "seed": args.seed,
            "semantic_boundary": (
                "selection asserts structural eligibility only; every retained task still "
                "requires an action-domain adapter and independent semantic review"
            ),
        },
        "eligible_count": eligible_count,
        "selected_count": len(selected),
        "selected_goal_signature_counts": _stable_counts(signatures),
        "selected_records": selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "selected_records"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
