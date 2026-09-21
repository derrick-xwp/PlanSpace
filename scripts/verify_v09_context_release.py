#!/usr/bin/env python3
"""Fail closed unless the six-model 171-task v0.9 bundle is complete."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.process_model_matrix_v0_2 import validate_raw_record
from scripts.verify_model_matrix_v0_2 import verify_matrix


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
CONFIG = ROOT / "configs" / "model_matrix_v0_9_context_171_six_model_gpuhub.json"
SUFFIX = "v0_9_context171_six"
TASK_COUNT = 171
SAMPLES_PER_TASK = 5


def load(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing v0.9 artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(result_dir: Path, *, require_paper_data: bool) -> None:
    config = load(CONFIG)
    assert config["artifact_suffix"] == SUFFIX
    assert config["task_count"] == TASK_COUNT
    assert config["evidence_status"] == (
        "v0_9_context_compatible_171_six_model_feasibility_filtered"
    )
    assert config["prompt_template"] == "uniform_compact_action_catalog_v1"
    assert config["fit_context"] is False
    feasibility = config["feasibility_filter"]
    assert feasibility["decision_independent_of_model_outputs"] is True
    audit_path = ROOT / feasibility["audit"]
    audit = load(audit_path)
    assert digest(audit_path) == feasibility["audit_sha256"]
    assert audit["retained_count"] == TASK_COUNT
    assert audit["excluded_count"] == 2
    verify_matrix(CONFIG, result_dir)

    queue = load(ROOT / config["queue"])
    assert queue["selected_count"] == TASK_COUNT
    assert queue["context_excluded_count"] == 2
    expected_sources = {row["source_path"]: row["source_sha256"] for row in queue["records"]}
    assert len(expected_sources) == TASK_COUNT
    shared_prompts: dict[str, str] = {}
    for model in config["models"]:
        raw_path = result_dir / (
            f"{model['slug']}_queue_{TASK_COUNT}_sampling_{SUFFIX}.json"
        )
        raw = load(raw_path)
        validate_raw_record(raw, model, config, expected_sources, shared_prompts, path=raw_path)
        assert raw["summary"]["completed_task_count"] == TASK_COUNT
        assert raw["summary"]["sample_count"] == TASK_COUNT * SAMPLES_PER_TASK
    assert len(shared_prompts) == TASK_COUNT

    if require_paper_data:
        generated = ROOT / "paper" / "generated_v09_context.tex"
        generated_structure = ROOT / "paper" / "generated_expanded_v09.tex"
        generated_cross_run = ROOT / "paper" / "generated_cross_run_v09.tex"
        generated_revision = ROOT / "paper" / "generated_revision_audits.tex"
        revision_manifest = ROOT / "paper" / "data" / "revision_audits_manifest.json"
        manuscript = ROOT / "paper" / "main.tex"
        assert generated.is_file()
        assert generated_structure.is_file()
        assert generated_cross_run.is_file()
        assert generated_revision.is_file()
        assert revision_manifest.is_file()
        assert r"\newcommand{\VTwoOutputCount}{5,130}" in generated.read_text(
            encoding="utf-8"
        )
        structure_text = generated_structure.read_text(encoding="utf-8")
        assert r"\newcommand{\ExpandedSupportedTaskCount}{171}" in structure_text
        assert r"\newcommand{\ExpandedExcludedTaskCount}{4}" in structure_text
        manuscript_text = manuscript.read_text(encoding="utf-8")
        assert r"\input{generated_v09_context.tex}" in manuscript_text
        assert r"\input{generated_expanded_v09.tex}" in manuscript_text
        assert r"\input{generated_cross_run_v09.tex}" in manuscript_text
        assert r"\input{generated_revision_audits.tex}" in manuscript_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=ARTIFACTS)
    parser.add_argument("--require-paper-data", action="store_true")
    args = parser.parse_args()
    verify(args.result_dir, require_paper_data=args.require_paper_data)
    print("six-model 171-task v0.9 release verified")


if __name__ == "__main__":
    main()
