#!/usr/bin/env python3
"""Verify provenance and agreement for the frozen v0.5 AI audit packets.

The audit packets are deliberately internal AI-assisted evidence.  This tool
does not turn the reviews into human validation or adjudicate their
disagreements; it checks that both completed packets arose from one frozen
input, that their recorded reviews can be reapplied exactly, and that the
published disagreement report is reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import types
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# ``scripts`` is intentionally a namespace package in this repository.  When
# this verifier is launched as a file, a third-party installed package of the
# same name can otherwise mask it.  Register the repository namespace before
# importing the shared validators so the command is standalone-reproducible.
namespace = types.ModuleType("scripts")
namespace.__path__ = [str(ROOT / "scripts")]
sys.modules["scripts"] = namespace

from scripts.analyze_semantic_review_agreement import BOOLEAN_FIELDS
from scripts.analyze_semantic_review_ai_agreement import analyze
from scripts.apply_semantic_review_ai_result import apply_result


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def frozen_packet(applied: dict) -> dict:
    packet = deepcopy(applied)
    packet.pop("evidence_status", None)
    packet.pop("evidence_boundary", None)
    for task in packet.get("tasks", []):
        task.pop("review", None)
    return packet


def reconstruct_result(applied: dict) -> dict:
    tasks = applied.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("applied audit must contain a non-empty task list")

    reviewers = set()
    kinds = set()
    dates = set()
    rows = []
    for task in tasks:
        review = task.get("review")
        if not isinstance(review, dict):
            raise ValueError("applied audit task lacks a review")
        reviewers.add(review.get("reviewer", ""))
        kinds.add(review.get("reviewer_kind", ""))
        dates.add(review.get("date", ""))
        rows.append(
            {
                "split": task.get("split"),
                "source_path": task.get("source_path"),
                **{field: review.get(field) for field in BOOLEAN_FIELDS},
                "decision": review.get("decision"),
                "notes": review.get("notes", ""),
            }
        )
    if len(reviewers) != 1 or not next(iter(reviewers), ""):
        raise ValueError("applied audit must contain exactly one reviewer identity")
    if kinds != {"codex_cli_ai"}:
        raise ValueError("applied audit must be marked codex_cli_ai")
    if len(dates) != 1 or not next(iter(dates), ""):
        raise ValueError("applied audit must contain exactly one review date")
    return {
        "reviewer_kind": "codex_cli_ai",
        "reviewer": next(iter(reviewers)),
        "date": next(iter(dates)),
        "rows": rows,
    }


def verify(left: dict, right: dict, agreement: dict) -> dict:
    left_frozen = frozen_packet(left)
    right_frozen = frozen_packet(right)
    left_frozen_hash = canonical_hash(left_frozen)
    right_frozen_hash = canonical_hash(right_frozen)
    if left_frozen_hash != right_frozen_hash:
        raise ValueError("the completed audits do not share an identical frozen input")

    left_reconstructed = apply_result(left_frozen, reconstruct_result(left))
    right_reconstructed = apply_result(right_frozen, reconstruct_result(right))
    if canonical_hash(left_reconstructed) != canonical_hash(left):
        raise ValueError("reviewer A packet does not reproduce through the application path")
    if canonical_hash(right_reconstructed) != canonical_hash(right):
        raise ValueError("reviewer B packet does not reproduce through the application path")

    recomputed = analyze(left, right)
    if canonical_hash(recomputed) != canonical_hash(agreement):
        raise ValueError("published AI-audit agreement report is not reproducible")

    return {
        "evidence_status": "verified_internal_ai_audit_consistency",
        "evidence_boundary": (
            "This report verifies internal AI-assisted audit provenance and agreement only; "
            "it is not independent human validation or an adjudication of disagreements."
        ),
        "task_count": left.get("task_count"),
        "frozen_input_sha256": left_frozen_hash,
        "reviewer_a_applied_packet_sha256": canonical_hash(left),
        "reviewer_b_applied_packet_sha256": canonical_hash(right),
        "agreement_report_sha256": canonical_hash(agreement),
        "application_reproducible": {"reviewer_a": True, "reviewer_b": True},
        "agreement_reproducible": True,
        "decision_disagreement_count": sum(
            item["field"] == "decision" for item in agreement["disagreements"]
        ),
        "disagreements": agreement["disagreements"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewer_a", type=Path)
    parser.add_argument("reviewer_b", type=Path)
    parser.add_argument("agreement", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = verify(
        json.loads(args.reviewer_a.read_text(encoding="utf-8")),
        json.loads(args.reviewer_b.read_text(encoding="utf-8")),
        json.loads(args.agreement.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "disagreements"}, indent=2))


if __name__ == "__main__":
    main()
