#!/usr/bin/env python3
"""Fail closed unless the six-model 173-task v0.8 bundle is complete."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.process_model_matrix_v0_2 import validate_raw_record
from scripts.verify_model_matrix_v0_2 import verify_matrix


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
CONFIG = ROOT / "configs" / "model_matrix_v0_8_expanded_173_six_model_gpuhub.json"
SUFFIX = "v0_8_expanded_six"
TASK_COUNT = 173
SAMPLES_PER_TASK = 5


def load(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing v0.8 artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify(result_dir: Path, *, require_paper_data: bool) -> None:
    config = load(CONFIG)
    assert config["artifact_suffix"] == SUFFIX
    assert config["task_count"] == TASK_COUNT
    assert config["evidence_status"] == "v0_8_expanded_173_six_model_uniform_compact_confirmatory"
    assert config["prompt_template"] == "uniform_compact_action_catalog_v1"
    assert config["fit_context"] is False
    verify_matrix(CONFIG, result_dir)

    queue = load(ROOT / config["queue"])
    expected_sources = {row["source_path"]: row["source_sha256"] for row in queue["records"]}
    assert len(expected_sources) == TASK_COUNT
    shared_prompts: dict[str, str] = {}
    for model in config["models"]:
        raw_path = result_dir / f"{model['slug']}_queue_{TASK_COUNT}_sampling_{SUFFIX}.json"
        raw = load(raw_path)
        validate_raw_record(raw, model, config, expected_sources, shared_prompts, path=raw_path)
        assert raw["summary"]["completed_task_count"] == TASK_COUNT
        assert raw["summary"]["sample_count"] == TASK_COUNT * SAMPLES_PER_TASK
    assert len(shared_prompts) == TASK_COUNT

    if require_paper_data:
        generated = ROOT / "paper" / "generated_v08_expanded.tex"
        generated_structure = ROOT / "paper" / "generated_expanded_v08.tex"
        generated_cross_run = ROOT / "paper" / "generated_cross_run_v08.tex"
        manuscript = ROOT / "paper" / "main.tex"
        assert generated.is_file()
        assert generated_structure.is_file()
        assert generated_cross_run.is_file()
        assert r"\newcommand{\VTwoOutputCount}{5,190}" in generated.read_text(encoding="utf-8")
        structure_text = generated_structure.read_text(encoding="utf-8")
        assert r"\newcommand{\ExpandedSupportedTaskCount}{173}" in structure_text
        manuscript_text = manuscript.read_text(encoding="utf-8")
        assert r"\input{generated_v08_expanded.tex}" in manuscript_text
        assert r"\input{generated_expanded_v08.tex}" in manuscript_text
        assert r"\input{generated_cross_run_v08.tex}" in manuscript_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=ARTIFACTS)
    parser.add_argument("--require-paper-data", action="store_true")
    args = parser.parse_args()
    verify(args.result_dir, require_paper_data=args.require_paper_data)
    print("six-model 173-task v0.8 release verified")


if __name__ == "__main__":
    main()
