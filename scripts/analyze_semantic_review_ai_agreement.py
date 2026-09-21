#!/usr/bin/env python3
"""Measure agreement between two isolated Codex CLI semantic audits."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.analyze_semantic_review_agreement import (
    BOOLEAN_FIELDS,
    DECISIONS,
    REVIEW_FIELDS,
    cohen_kappa,
    task_id,
)


AI_STATUS = "completed_independent_codex_cli_ai_review"


def validate_ai_packet(packet: dict, label: str) -> tuple[dict[str, dict], str]:
    if packet.get("evidence_status") != AI_STATUS:
        raise ValueError(f"{label} is not completed Codex CLI AI audit evidence")
    tasks = packet.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError(f"{label} has no review tasks")
    indexed = {}
    reviewers = set()
    for task in tasks:
        identifier = task_id(task)
        if identifier in indexed:
            raise ValueError(f"{label} duplicates {identifier}")
        review = task.get("review", {})
        if review.get("reviewer_kind") != "codex_cli_ai":
            raise ValueError(f"{label} {identifier} is not marked codex_cli_ai")
        for field in BOOLEAN_FIELDS:
            if not isinstance(review.get(field), bool):
                raise ValueError(f"{label} {identifier} lacks boolean {field}")
        if review.get("decision") not in DECISIONS:
            raise ValueError(f"{label} {identifier} has invalid decision")
        reviewer = review.get("reviewer", "").strip()
        if not reviewer:
            raise ValueError(f"{label} {identifier} lacks reviewer identity")
        reviewers.add(reviewer)
        indexed[identifier] = review
    if len(reviewers) != 1:
        raise ValueError(f"{label} must contain exactly one reviewer identity")
    return indexed, next(iter(reviewers))


def analyze(left_packet: dict, right_packet: dict) -> dict:
    for field in ("packet_version", "generic_domain_version", "split_version"):
        if left_packet.get(field) != right_packet.get(field):
            raise ValueError(f"packet mismatch in {field}")
    left, left_name = validate_ai_packet(left_packet, "AI reviewer A packet")
    right, right_name = validate_ai_packet(right_packet, "AI reviewer B packet")
    if left_name == right_name:
        raise ValueError("AI reviewer identities must differ")
    if set(left) != set(right):
        raise ValueError("AI packets do not contain identical task IDs")

    identifiers = sorted(left)
    per_field = {}
    disagreements = []
    for field in REVIEW_FIELDS:
        lv = [left[item][field] for item in identifiers]
        rv = [right[item][field] for item in identifiers]
        agreed = sum(a == b for a, b in zip(lv, rv))
        per_field[field] = {
            "agreement_count": agreed,
            "task_count": len(identifiers),
            "agreement_rate": agreed / len(identifiers),
            "cohen_kappa": cohen_kappa(lv, rv),
            "reviewer_a_distribution": dict(sorted(Counter(lv).items(), key=lambda x: str(x[0]))),
            "reviewer_b_distribution": dict(sorted(Counter(rv).items(), key=lambda x: str(x[0]))),
        }
        for identifier, a, b in zip(identifiers, lv, rv):
            if a != b:
                disagreements.append(
                    {"task_id": identifier, "field": field, "reviewer_a": a, "reviewer_b": b}
                )
    return {
        "evidence_status": "independent_codex_cli_ai_audit_agreement",
        "packet_version": left_packet["packet_version"],
        "task_count": len(identifiers),
        "reviewer_a": left_name,
        "reviewer_b": right_name,
        "per_field": per_field,
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
        "boundary": (
            "Agreement measures two isolated AI audits. It is not human construct "
            "validation, external approval, or evidence of low-level feasibility."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewer_a", type=Path)
    parser.add_argument("reviewer_b", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(
        json.loads(args.reviewer_a.read_text(encoding="utf-8")),
        json.loads(args.reviewer_b.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "disagreements"}, indent=2))


if __name__ == "__main__":
    main()
