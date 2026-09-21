#!/usr/bin/env python3
"""Fail closed unless the semantic-v0.4 six-model release is reproducible.

This gate deliberately treats the two Codex CLI audits as internal AI evidence,
not as human construct validation.  The manuscript must preserve that boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.analyze_semantic_review_ai_agreement import analyze as analyze_ai_agreement
from scripts.process_model_matrix_v0_2 import validate_raw_record
from scripts.verify_model_matrix_v0_2 import verify_matrix
from scripts.verify_v04_claims import verify as verify_claims


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
CONFIG = ROOT / "configs" / "model_matrix_v0_4.json"
SUFFIX = "v0_4"


def load(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing v0.4 artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_ai_semantic_gate() -> None:
    left_path = ARTIFACTS / "semantic_review_codex_astra_a_v0_4.json"
    right_path = ARTIFACTS / "semantic_review_codex_sol_b_v0_4.json"
    agreement_path = ARTIFACTS / "semantic_review_codex_ai_agreement_v0_4.json"
    left, right, recorded = map(load, (left_path, right_path, agreement_path))
    recomputed = json.loads(json.dumps(analyze_ai_agreement(left, right)))
    assert recorded == recomputed, "AI agreement report is stale or tampered"
    assert recorded["evidence_status"] == "independent_codex_cli_ai_audit_agreement"
    assert recorded["task_count"] == 30
    assert recorded["reviewer_a"] != recorded["reviewer_b"]
    assert "not human construct validation" in recorded["boundary"]

    adjudication = load(ARTIFACTS / "semantic_review_v0_4_adjudication.json")
    gate = adjudication["gate"]
    assert gate["passed"] is True
    assert gate["observed_decision_agreement"] >= gate["required_decision_agreement"]
    assert gate["reject_count"] == 0 and gate["p0_invariant_defect_count"] == 0
    assert adjudication["packet_version"] == recorded["packet_version"]
    assert adjudication["items"], "localized AI disagreement must be disclosed"
    assert all("paper_boundary" in item for item in adjudication["items"])


def verify(result_dir: Path, *, require_paper_data: bool) -> None:
    config = load(CONFIG)
    assert config["artifact_suffix"] == SUFFIX
    assert config["evidence_status"] == "v0_4_model_run_after_internal_ai_semantic_gate"
    verify_ai_semantic_gate()
    verify_matrix(CONFIG, result_dir)

    queue = load(ROOT / config["queue"])
    expected_sources = {row["source_path"]: row["source_sha256"] for row in queue["records"]}
    assert len(expected_sources) == 100
    shared_prompts: dict[str, str] = {}
    for model in config["models"]:
        slug = model["slug"]
        raw_path = result_dir / f"{slug}_queue_100_sampling_{SUFFIX}.json"
        raw = load(raw_path)
        validate_raw_record(raw, model, config, expected_sources, shared_prompts, path=raw_path)
        # The runner records additional aggregate rates and timing fields in
        # the summary.  The release gate checks the required cardinalities
        # without rejecting those auditable extensions.
        assert raw["summary"]["completed_task_count"] == 100
        assert raw["summary"]["sample_count"] == 500

    if require_paper_data:
        generated = ROOT / "paper" / "generated_v04.tex"
        manuscript = ROOT / "paper" / "main.tex"
        tables = ROOT / "paper" / "results_v04_tables.tex"
        assert generated.is_file() and tables.is_file()
        assert "from v0_4; do not edit." in generated.read_text(encoding="utf-8")
        manuscript_text = manuscript.read_text(encoding="utf-8")
        table_text = tables.read_text(encoding="utf-8")
        if r"\input{results_v02_tables.tex}" in table_text:
            table_text += "\n" + (ROOT / "paper" / "results_v02_tables.tex").read_text(
                encoding="utf-8"
            )
        assert r"\input{generated_v04.tex}" in manuscript_text
        assert r"\input{results_v04_tables.tex}" in manuscript_text
        # The table macros are intentionally stable despite the new file name.
        for macro in (r"\VTwoModelRows", r"\VTwoSensitivityRows", r"\VTwoAllPairRows"):
            assert macro in table_text
        assert "two-human review" not in manuscript_text
        assert "not independent human validation" in manuscript_text
        verify_claims(manuscript, generated)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=ARTIFACTS)
    parser.add_argument("--require-paper-data", action="store_true")
    args = parser.parse_args()
    verify(args.result_dir, require_paper_data=args.require_paper_data)
    print("six-model v0.4 release verified")


if __name__ == "__main__":
    main()
