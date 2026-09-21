#!/usr/bin/env python3
"""Build a metric-label-blind adjudication packet for reviewer disagreements."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


FIELDS = (
    "interface_compliant",
    "valid_at_declared_abstraction",
    "reasonable_high_level_behavior",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("reviewer_a", type=Path)
    parser.add_argument("reviewer_b", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    left = json.loads(args.reviewer_a.read_text(encoding="utf-8"))
    right = json.loads(args.reviewer_b.read_text(encoding="utf-8"))
    ids = [case["audit_id"] for case in packet["cases"]]
    left_by_id = {row["audit_id"]: row for row in left["reviews"]}
    right_by_id = {row["audit_id"]: row for row in right["reviews"]}
    if list(left_by_id) != ids or list(right_by_id) != ids:
        raise ValueError("review IDs/order do not match the public packet")

    disagreements = []
    for case in packet["cases"]:
        audit_id = case["audit_id"]
        a, b = left_by_id[audit_id], right_by_id[audit_id]
        fields = [field for field in FIELDS if a[field] != b[field]]
        if fields:
            disagreements.append(
                {
                    "audit_id": audit_id,
                    "disputed_fields": fields,
                    "case": case,
                    "reviewer_a": a,
                    "reviewer_b": b,
                }
            )
    result = {
        "packet_version": "planspace-output-validity-adjudication-v0.1",
        "source_packet_version": packet["packet_version"],
        "evidence_status": "metric_label_blind_internal_ai_adjudication_packet",
        "reviewer_a_role": left["reviewer_role"],
        "reviewer_b_role": right["reviewer_role"],
        "disagreement_case_count": len(disagreements),
        "cases": disagreements,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(disagreements)} disagreement cases")


if __name__ == "__main__":
    main()
