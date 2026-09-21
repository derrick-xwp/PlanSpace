#!/usr/bin/env python3
"""Fail closed unless all three post-hoc ICLR revision audits are consistent."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
PAPER = ROOT / "paper"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing revision audit artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify() -> None:
    sources = {
        "independent_state_search": ARTIFACTS / "independent_state_search_v0_1.json",
        "partial_order_cap_sensitivity": ARTIFACTS / "partial_order_cap_sensitivity_v0_1.json",
        "cost_bounded_goal_validity": ARTIFACTS / "cost_bounded_goal_validity_v0_1.json",
    }
    records = {name: load(path) for name, path in sources.items()}
    independent = records["independent_state_search"]
    assert independent["summary"]["task_count"] == 171
    assert independent["summary"]["tasks_with_independent_nonreference_solution"] > 0
    assert independent["evidence_status"] == "post_hoc_independent_algorithmic_validation"

    cap = records["partial_order_cap_sensitivity"]
    assert cap["summary"]["task_count"] == 171
    assert cap["caps"] == [100, 500, 1000, 2000]
    assert cap["summary"]["all_checked_orders_valid_at_every_cap"] is True
    assert "does not enumerate orders" in cap["metric_boundary"]

    cost = records["cost_bounded_goal_validity"]
    assert len(cost["models"]) == 6
    assert sum(model["output_count"] for model in cost["models"]) == 5130
    assert cost["thresholds"] == [0.0, 0.25, 0.5, 1.0]

    manifest = load(PAPER / "data" / "revision_audits_manifest.json")
    manifest_by_name = {row["name"]: row for row in manifest["audits"]}
    assert set(manifest_by_name) == set(sources)
    for name, path in sources.items():
        assert manifest_by_name[name]["sha256"] == digest(path)

    generated = (PAPER / "generated_revision_audits.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\IndependentSearchTaskCount}{171}" in generated
    assert r"\newcommand{\CapSensitiveAllValid}{true}" in generated
    manuscript = (PAPER / "main.tex").read_text(encoding="utf-8")
    assert r"\input{generated_revision_audits.tex}" in manuscript


if __name__ == "__main__":
    verify()
    print("revision audits verified")
