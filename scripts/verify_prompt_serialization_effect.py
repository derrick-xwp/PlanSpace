#!/usr/bin/env python3
"""Fail closed unless the controlled prompt-serialization analysis is reproducible."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from scripts.analyze_prompt_serialization_effect import METRICS, load_condition, paired_effect
from scripts.compare_model_matrix import holm_adjust


ROOT = Path(__file__).resolve().parents[1]
OLD_CONFIG = ROOT / "configs" / "model_matrix_v0_4.json"
NEW_CONFIG = ROOT / "configs" / "model_matrix_v0_6_v04_uniform_compact.json"


def assert_effect_equal(actual: dict, expected: dict) -> None:
    """Compare recomputed statistics across Python versions without masking drift."""
    assert actual.keys() == expected.keys()
    for key in actual:
        if isinstance(actual[key], float):
            assert math.isclose(actual[key], expected[key], rel_tol=0.0, abs_tol=1e-12), (
                key,
                actual[key],
                expected[key],
            )
        else:
            assert actual[key] == expected[key]


def verify(result_dir: Path, report_path: Path, *, require_paper_data: bool = False) -> None:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    old_config, old_reports = load_condition(OLD_CONFIG, result_dir)
    new_config, new_reports = load_condition(NEW_CONFIG, result_dir)
    assert report["evidence_status"] == "controlled_same_seed_same_domain_prompt_serialization_comparison"
    assert report["old_protocol_version"] == old_config["protocol_version"]
    assert report["new_protocol_version"] == new_config["protocol_version"]
    assert report["generic_domain_version"] == old_config["generic_domain_version"] == new_config["generic_domain_version"]
    assert report["decoding"] == old_config["decoding"] == new_config["decoding"]
    assert report["bootstrap"]["unit"] == "paired task"
    assert report["bootstrap"]["trials"] == 10_000
    trials = report["bootstrap"]["trials"]
    base_seed = report["bootstrap"]["seed"]
    rows = {row["model_id"]: row for row in report["models"]}
    assert set(rows) == set(old_reports) == set(new_reports)

    recomputed: dict[str, dict[str, dict]] = {}
    for model_index, model_id in enumerate(old_reports):
        row = rows[model_id]
        assert row["model_revision"] == old_reports[model_id]["model_revision"] == new_reports[model_id]["model_revision"]
        old_tasks = {task["source_path"]: task for task in old_reports[model_id]["tasks"]}
        new_tasks = {task["source_path"]: task for task in new_reports[model_id]["tasks"]}
        assert row["task_count"] == len(old_tasks) == len(new_tasks) == 100
        assert row["prompt_hash_changed_task_count"] == sum(
            old_tasks[path]["prompt_sha256"] != new_tasks[path]["prompt_sha256"]
            for path in old_tasks
        )
        assert row["serialized_chat_hash_changed_task_count"] == sum(
            old_tasks[path]["serialized_chat_sha256"]
            != new_tasks[path]["serialized_chat_sha256"]
            for path in old_tasks
        )
        recomputed[model_id] = {
            metric: paired_effect(
                old_tasks,
                new_tasks,
                metric,
                trials=trials,
                seed=base_seed + model_index * 100 + metric_index,
            )
            for metric_index, metric in enumerate(METRICS)
        }
    for metric in METRICS:
        adjusted = holm_adjust(
            [recomputed[model_id][metric]["paired_sign_flip_p_value"] for model_id in old_reports]
        )
        for model_id, adjusted_p in zip(old_reports, adjusted):
            expected = {
                **recomputed[model_id][metric],
                "holm_adjusted_p_value": adjusted_p,
                "holm_reject_0_05": adjusted_p < 0.05,
            }
            assert_effect_equal(rows[model_id]["effects"][metric], expected)
    if require_paper_data:
        generated = ROOT / "paper" / "generated_prompt_effect.tex"
        manuscript = ROOT / "paper" / "main.tex"
        assert generated.is_file()
        text = manuscript.read_text(encoding="utf-8")
        assert r"\input{generated_prompt_effect.tex}" in text
        assert r"\PromptSerializationEffectTable" in text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=ROOT / "artifacts")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "artifacts" / "prompt_serialization_effect_v0_6.json",
    )
    parser.add_argument("--require-paper-data", action="store_true")
    args = parser.parse_args()
    verify(args.result_dir, args.report, require_paper_data=args.require_paper_data)
    print("controlled prompt-serialization effect verified")


if __name__ == "__main__":
    main()
