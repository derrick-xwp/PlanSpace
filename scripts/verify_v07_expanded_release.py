#!/usr/bin/env python3
"""Verify the 173-task Qwen3-8B expanded-coverage experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.process_model_matrix_v0_2 import validate_raw_record


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
CONFIG = ROOT / "configs" / "model_matrix_v0_7_expanded_173_gpuhub.json"


def load(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing expanded artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify(result_dir: Path, *, require_paper_data: bool = False) -> None:
    config = load(CONFIG)
    assert config["task_count"] == 173
    assert config["protocol_version"] == "planspace_text_plan_v0.6-v04-uniform-compact"
    assert config["generic_domain_version"] == "planspace_generic_household_v0.4-candidate"
    assert len(config["models"]) == 1
    model = config["models"][0]
    assert model["model_id"] == "Qwen/Qwen3-8B"

    queue = load(ROOT / config["queue"])
    assert queue["selected_count"] == len(queue["records"]) == 173
    assert queue["excluded_count"] == len(queue["excluded"]) == 2
    assert {row["source_path"] for row in queue["excluded"]} == {
        "collecting_berries/problem0.bddl",
        "store_christmas_lights/problem0.bddl",
    }
    expected_sources = {row["source_path"]: row["source_sha256"] for row in queue["records"]}

    slug = model["slug"]
    suffix = config["artifact_suffix"]
    raw_path = result_dir / f"{slug}_queue_173_sampling_{suffix}.json"
    raw = load(raw_path)
    validate_raw_record(raw, model, config, expected_sources, {}, path=raw_path)
    assert raw["summary"]["completed_task_count"] == 173
    assert raw["summary"]["sample_count"] == 865

    enriched = load(result_dir / f"{slug}_queue_173_enriched_{suffix}.json")
    analysis = load(result_dir / f"{slug}_queue_173_analysis_{suffix}.json")
    assert len(enriched["tasks"]) == 173
    assert analysis["bootstrap"]["trials"] == 10_000
    assert sum(analysis["failure_counts"].values()) == 865
    assert sum(
        row["task_count"] for row in analysis["strata"]["structural_split"].values()
    ) == 173
    assert len(load(result_dir / f"multi_model_comparison_{suffix}.json")["aggregate"]) == 1
    if require_paper_data:
        generated = ROOT / "paper" / "generated_expanded_v07.tex"
        manuscript = ROOT / "paper" / "main.tex"
        assert generated.is_file()
        text = manuscript.read_text(encoding="utf-8")
        assert r"\input{generated_expanded_v07.tex}" in text
        assert "compatibility-filtered" in text
    print("173-task expanded-coverage release verified")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=ARTIFACTS)
    parser.add_argument("--require-paper-data", action="store_true")
    args = parser.parse_args()
    verify(args.result_dir, require_paper_data=args.require_paper_data)


if __name__ == "__main__":
    main()
