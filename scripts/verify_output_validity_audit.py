#!/usr/bin/env python3
"""Fail closed unless the blinded output-validity audit is complete and reproducible."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
FIELDS = (
    "interface_compliant",
    "valid_at_declared_abstraction",
    "reasonable_high_level_behavior",
)


def load(name: str) -> dict:
    path = ARTIFACTS / name
    if not path.is_file():
        raise AssertionError(f"missing audit artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    packet = load("output_validity_audit_packet_v0_1.json")
    manifest = load("output_validity_metric_manifest_v0_1.json")
    left = load("output_validity_codex_formal_v0_1.json")
    right = load("output_validity_codex_adversarial_v0_1.json")
    adjudication_packet = load("output_validity_adjudication_packet_v0_1.json")
    adjudication = load("output_validity_codex_adjudication_v0_1.json")
    recorded = load("output_validity_ai_adjudicated_v0_1.json")

    ids = [case["audit_id"] for case in packet["cases"]]
    assert len(ids) == len(set(ids)) == 120
    assert [case["audit_id"] for case in manifest["cases"]] == ids
    public_text = json.dumps(packet)
    for forbidden in (
        '"hidden_category"',
        '"model_id"',
        '"reference_plan"',
        '"exact_match"',
        '"partial_order_match"',
        '"goal_valid"',
        '"ordered_action_similarity"',
    ):
        assert forbidden not in public_text, f"public packet leaks {forbidden}"

    left_ids = [row["audit_id"] for row in left["reviews"]]
    right_ids = [row["audit_id"] for row in right["reviews"]]
    assert left_ids == right_ids == ids
    assert left["reviewer_role"] != right["reviewer_role"]
    disagreement_ids = [
        audit_id
        for audit_id, a, b in zip(ids, left["reviews"], right["reviews"])
        if any(a[field] != b[field] for field in FIELDS)
    ]
    assert adjudication_packet["disagreement_case_count"] == len(disagreement_ids) == 23
    assert [row["audit_id"] for row in adjudication_packet["cases"]] == disagreement_ids
    assert [row["audit_id"] for row in adjudication["decisions"]] == disagreement_ids

    with tempfile.TemporaryDirectory(prefix="planspace-output-audit-") as temporary:
        output = Path(temporary) / "analysis.json"
        table = Path(temporary) / "analysis.md"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "analyze_metric_validity_audit.py"),
                str(ARTIFACTS / "output_validity_metric_manifest_v0_1.json"),
                str(ARTIFACTS / "output_validity_codex_formal_v0_1.json"),
                str(ARTIFACTS / "output_validity_codex_adversarial_v0_1.json"),
                "--adjudication",
                str(ARTIFACTS / "output_validity_codex_adjudication_v0_1.json"),
                "--output",
                str(output),
                "--table-output",
                str(table),
            ],
            cwd=ROOT,
            check=True,
        )
        assert json.loads(output.read_text(encoding="utf-8")) == recorded

    assert recorded["case_count"] == recorded["consensus_reasonable_case_count"] == 120
    assert recorded["adjudication_case_count"] == 23
    metrics = recorded["metric_validity_against_ai_consensus"]
    assert metrics["goal_valid"]["recall"] > metrics["partial_order_match"]["recall"]
    assert metrics["partial_order_match"]["recall"] > metrics["exact_match"]["recall"]
    assert "not independent human or simulator construct validity" in recorded["boundary"]
    print("output-validity audit verified")


if __name__ == "__main__":
    main()
