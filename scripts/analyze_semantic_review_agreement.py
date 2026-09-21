#!/usr/bin/env python3
"""Measure agreement between two independently completed semantics packets.

The analyzer deliberately fails closed: missing labels, duplicate task IDs, packet
version drift, or reviewer-name reuse prevent an agreement report from being
created.  Automatic replay is never treated as a human semantic judgment.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REVIEW_FIELDS = (
    "source_to_compiled_goal",
    "action_preconditions",
    "action_effects",
    "trace_plausibility_at_declared_abstraction",
    "selective_closed_world_assumptions",
    "decision",
)
BOOLEAN_FIELDS = set(REVIEW_FIELDS[:-1])
DECISIONS = {"approve", "revise", "reject"}


def task_id(task: dict) -> str:
    return f"{task['split']}::{task['source_path']}"


def cohen_kappa(left: list[object], right: list[object]) -> float | None:
    """Return unweighted Cohen's kappa, or None when chance agreement is 1."""

    if len(left) != len(right) or not left:
        raise ValueError("paired non-empty label vectors are required")
    labels = sorted(set(left) | set(right), key=str)
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum(
        (left_counts[label] / len(left)) * (right_counts[label] / len(right))
        for label in labels
    )
    if expected == 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def validate_packet(packet: dict, label: str) -> dict[str, dict]:
    if packet.get("evidence_status") != "completed_independent_review":
        raise ValueError(
            f"{label} is not completed human review evidence: "
            f"{packet.get('evidence_status')!r}"
        )
    tasks = packet.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError(f"{label} has no review tasks")
    indexed: dict[str, dict] = {}
    reviewers = set()
    for task in tasks:
        identifier = task_id(task)
        if identifier in indexed:
            raise ValueError(f"{label} duplicates {identifier}")
        review = task.get("review", {})
        if review.get("reviewer_kind") not in (None, "human"):
            raise ValueError(f"{label} {identifier} is not a human review")
        for field in REVIEW_FIELDS:
            value = review.get(field)
            if field in BOOLEAN_FIELDS and not isinstance(value, bool):
                raise ValueError(f"{label} {identifier} lacks boolean {field}")
            if field == "decision" and value not in DECISIONS:
                raise ValueError(f"{label} {identifier} has invalid decision {value!r}")
        reviewer = review.get("reviewer")
        date = review.get("date")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError(f"{label} {identifier} lacks reviewer identity")
        if not isinstance(date, str) or not date.strip():
            raise ValueError(f"{label} {identifier} lacks review date")
        reviewers.add(reviewer.strip())
        indexed[identifier] = review
    if len(reviewers) != 1:
        raise ValueError(f"{label} must contain exactly one reviewer identity")
    return indexed


def analyze(left_packet: dict, right_packet: dict) -> dict:
    for field in ("packet_version", "generic_domain_version", "split_version"):
        if left_packet.get(field) != right_packet.get(field):
            raise ValueError(f"packet mismatch in {field}")

    left = validate_packet(left_packet, "reviewer A packet")
    right = validate_packet(right_packet, "reviewer B packet")
    if set(left) != set(right):
        raise ValueError("reviewer packets do not contain identical task IDs")
    left_names = {review["reviewer"].strip() for review in left.values()}
    right_names = {review["reviewer"].strip() for review in right.values()}
    if left_names == right_names:
        raise ValueError("reviewer A and reviewer B must be different people")

    identifiers = sorted(left)
    per_field = {}
    disagreements = []
    for field in REVIEW_FIELDS:
        left_values = [left[item][field] for item in identifiers]
        right_values = [right[item][field] for item in identifiers]
        agreed = sum(a == b for a, b in zip(left_values, right_values))
        per_field[field] = {
            "agreement_count": agreed,
            "task_count": len(identifiers),
            "agreement_rate": agreed / len(identifiers),
            "cohen_kappa": cohen_kappa(left_values, right_values),
            "reviewer_a_distribution": dict(sorted(Counter(left_values).items(), key=lambda x: str(x[0]))),
            "reviewer_b_distribution": dict(sorted(Counter(right_values).items(), key=lambda x: str(x[0]))),
        }
        for identifier, a, b in zip(identifiers, left_values, right_values):
            if a != b:
                disagreements.append(
                    {"task_id": identifier, "field": field, "reviewer_a": a, "reviewer_b": b}
                )

    return {
        "evidence_status": "independent_review_agreement_before_adjudication",
        "packet_version": left_packet["packet_version"],
        "task_count": len(identifiers),
        "reviewer_a": next(iter(left_names)),
        "reviewer_b": next(iter(right_names)),
        "per_field": per_field,
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
        "boundary": (
            "Agreement quantifies consistency between two human judgments. It does not "
            "establish low-level motion feasibility or real-robot executability."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewer_a", type=Path)
    parser.add_argument("reviewer_b", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    left = json.loads(args.reviewer_a.read_text(encoding="utf-8"))
    right = json.loads(args.reviewer_b.read_text(encoding="utf-8"))
    report = analyze(left, right)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "disagreements"}, indent=2))


if __name__ == "__main__":
    main()
