#!/usr/bin/env python3
"""Fail closed unless the controlled v0.6 uniform-prompt matrix is complete."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.process_model_matrix_v0_2 import validate_raw_record
from scripts.verify_model_matrix_v0_2 import verify_matrix


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
CONFIG = ROOT / "configs" / "model_matrix_v0_6_v04_uniform_compact.json"
SUFFIX = "v0_6"


def load(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing v0.6 artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify(result_dir: Path, *, require_paper_data: bool) -> None:
    config = load(CONFIG)
    assert config["artifact_suffix"] == SUFFIX
    assert config["protocol_version"] == "planspace_text_plan_v0.6-v04-uniform-compact"
    assert config["evidence_status"] == "v0_6_v04_uniform_compact_controlled_rerun"
    assert config["prompt_template"] == "uniform_compact_action_catalog_v1"
    assert config["fit_context"] is False
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
        assert raw["summary"]["completed_task_count"] == 100
        assert raw["summary"]["sample_count"] == 500
    assert len(shared_prompts) == 100

    comparison = load(result_dir / f"multi_model_comparison_{SUFFIX}.json")
    assert len(comparison["aggregate"]) == 6
    assert len(comparison["paired_comparisons"]) == 15
    sampling = load(result_dir / f"sampling_curve_analysis_{SUFFIX}.json")
    assert len(sampling["models"]) == 6

    if require_paper_data:
        generated = ROOT / "paper" / "generated_v06.tex"
        tables = ROOT / "paper" / "results_v06_tables.tex"
        manuscript = ROOT / "paper" / "main.tex"
        assert generated.is_file() and tables.is_file()
        text = manuscript.read_text(encoding="utf-8")
        assert r"\input{generated_v06.tex}" in text
        assert r"\input{results_v06_tables.tex}" in text
        assert "rather than independent human annotators" in text
        assert "adversarial consistency check" in text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=ARTIFACTS)
    parser.add_argument("--require-paper-data", action="store_true")
    args = parser.parse_args()
    verify(args.result_dir, require_paper_data=args.require_paper_data)
    print("controlled six-model v0.6 release verified")


if __name__ == "__main__":
    main()
