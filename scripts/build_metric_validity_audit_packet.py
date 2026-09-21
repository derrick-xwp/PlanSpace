#!/usr/bin/env python3
"""Build a blinded, stratified output-level validity audit packet."""
from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import hashlib
import json
from collections import defaultdict
from pathlib import Path


QUOTAS = {
    "valid_exact": 20,
    "valid_nonexact_in_family": 20,
    "valid_nonexact_outside_family": 20,
    "executable_goal_miss": 20,
    "precondition_failure": 20,
    "parse_failure": 20,
}


def category(sample: dict) -> str:
    if sample.get("parse_error") is not None:
        return "parse_failure"
    execution = sample.get("execution") or {}
    if not execution.get("executable"):
        return "precondition_failure"
    if not execution.get("goal_satisfied"):
        return "executable_goal_miss"
    if sample.get("exact_match"):
        return "valid_exact"
    if sample.get("partial_order_match"):
        return "valid_nonexact_in_family"
    return "valid_nonexact_outside_family"


def stable_key(row: dict) -> str:
    text = "|".join(
        (
            row["model_id"],
            row["source_path"],
            str(row["sample"]["seed"]),
            str(row["sample"]["sample_index"]),
        )
    )
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--inputs", required=True, nargs="+", type=Path)
    parser.add_argument("--packet-output", required=True, type=Path)
    parser.add_argument("--manifest-output", required=True, type=Path)
    args = parser.parse_args()

    metadata_report = json.loads(args.metadata.read_text(encoding="utf-8"))
    metadata_by_path = {task["source_path"]: task for task in metadata_report["tasks"]}
    pools: dict[str, list[dict]] = defaultdict(list)
    for path in args.inputs:
        report = json.loads(path.read_text(encoding="utf-8"))
        for task in report["tasks"]:
            for sample in task["samples"]:
                row = {
                    "model_id": report["model_id"],
                    "model_revision": report["model_revision"],
                    "source_path": task["source_path"],
                    "source_sha256": task["source_sha256"],
                    "sample": sample,
                }
                pools[category(sample)].append(row)

    selected = []
    for label, requested in QUOTAS.items():
        candidates = sorted(pools[label], key=stable_key)
        selected.extend((label, row) for row in candidates[:requested])
    selected.sort(key=lambda item: stable_key(item[1]))

    cases = []
    manifest_cases = []
    for index, (label, row) in enumerate(selected, 1):
        audit_id = f"output-validity-{index:03d}"
        sample = row["sample"]
        task = metadata_by_path[row["source_path"]]
        cases.append(
            {
                "audit_id": audit_id,
                "source_path": row["source_path"],
                "source_sha256": row["source_sha256"],
                "structural_split": task["split"],
                "source_goal_expression": task["source_goal_expression"],
                "compiled_initial_state": task["compiled_initial_state"],
                "compiled_goal_alternatives": task["compiled_goal_alternatives"],
                "declared_actions": task["actions"],
                "model_output": sample["raw_output"],
                "parsed_plan": sample.get("parsed_plan"),
                "parser_message": sample.get("parse_error"),
            }
        )
        manifest_cases.append(
            {
                "audit_id": audit_id,
                "model_id": row["model_id"],
                "model_revision": row["model_revision"],
                "source_path": row["source_path"],
                "sample_index": sample["sample_index"],
                "seed": sample["seed"],
                "hidden_category": label,
                "exact_match": bool(sample.get("exact_match")),
                "partial_order_match": bool(sample.get("partial_order_match")),
                "goal_valid": bool((sample.get("execution") or {}).get("valid")),
                "ordered_action_similarity": SequenceMatcher(
                    a=task["review_trace"], b=sample.get("parsed_plan") or []
                ).ratio(),
            }
        )

    packet = {
        "evidence_status": "blinded_output_validity_packet_pending_ai_audit",
        "packet_version": "planspace-output-validity-v0.1",
        "case_count": len(cases),
        "selection_rule": (
            "Deterministic SHA-256-ranked sample from six mutually exclusive evaluator "
            "outcome strata. Metric labels, model identity, reference plans, and outcome "
            "strata are withheld from reviewers. Strata with fewer available cases are "
            "included exhaustively."
        ),
        "review_boundary": (
            "Judge high-level household-task validity from the source goal, declared initial "
            "state, and declared action semantics. This audit does not establish geometric, "
            "motion-planning, or robot feasibility."
        ),
        "cases": cases,
    }
    manifest = {
        "evidence_status": "private_metric_manifest_not_provided_to_reviewers",
        "packet_version": packet["packet_version"],
        "requested_quotas": QUOTAS,
        "available_counts": {key: len(pools[key]) for key in QUOTAS},
        "selected_counts": {
            key: sum(case["hidden_category"] == key for case in manifest_cases)
            for key in QUOTAS
        },
        "cases": manifest_cases,
    }
    args.packet_output.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    args.manifest_output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_count": len(cases), **manifest["selected_counts"]}, indent=2))


if __name__ == "__main__":
    main()
