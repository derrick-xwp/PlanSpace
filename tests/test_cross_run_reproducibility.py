from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cross_run", ROOT / "scripts" / "analyze_cross_run_reproducibility.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def record(raw_output="x", *, seed=1, goal=True):
    return {
        "model_id": "m",
        "model_revision": "r",
        "protocol_version": "p",
        "generic_domain_version": "d",
        "decoding": {"samples_per_task": 1},
        "tasks": [
            {
                "source_path": "a/problem0.bddl",
                "source_sha256": "s",
                "prompt_sha256": "p",
                "serialized_chat_sha256": "c",
                "samples": [
                    {
                        "sample_index": 0,
                        "seed": seed,
                        "raw_output": raw_output,
                        "parsed_plan": [],
                        "parse_error": None,
                        "exact_match": goal,
                        "execution": {
                            "executable": goal,
                            "valid": goal,
                        },
                    }
                ],
            }
        ],
    }


def test_summarize_model_reports_output_and_metric_drift():
    old = record()
    new = record("y", goal=False)
    summary = MODULE.summarize_model(old, new, {"a/problem0.bddl"})
    assert summary["raw_output_match_rate"] == 0
    assert summary["all_samples_match_task_count"] == 0
    assert summary["metrics"]["goal_valid"]["new_minus_old"] == -1


def test_summarize_model_fails_on_identity_drift():
    old = record()
    new = deepcopy(old)
    new["model_revision"] = "other"
    with pytest.raises(ValueError, match="identity"):
        MODULE.summarize_model(old, new, {"a/problem0.bddl"})


def test_analyze_accepts_legacy_null_task_count(tmp_path):
    model = {
        "slug": "m",
        "model_id": "m",
        "revision": "r",
        "local_dir": "m",
        "prompt_policy": "p",
    }
    old_config = {
        "matrix_version": "old",
        "artifact_suffix": "old",
        "task_count": None,
        "models": [model],
    }
    new_config = {
        "matrix_version": "new",
        "artifact_suffix": "new",
        "task_count": 100,
        "models": [model],
    }
    tasks = []
    for index in range(100):
        item = record()["tasks"][0]
        item = deepcopy(item)
        item["source_path"] = f"task_{index}/problem0.bddl"
        item["source_sha256"] = f"sha-{index}"
        tasks.append(item)
    old_record = record()
    new_record = record()
    old_record["tasks"] = deepcopy(tasks)
    new_record["tasks"] = deepcopy(tasks)
    (tmp_path / "m_queue_100_sampling_old.json").write_text(
        __import__("json").dumps(old_record), encoding="utf-8"
    )
    (tmp_path / "m_queue_100_sampling_new.json").write_text(
        __import__("json").dumps(new_record), encoding="utf-8"
    )
    result = MODULE.analyze(old_config, new_config, tmp_path, tmp_path)
    assert result["overlap_task_count"] == 100


def test_analyze_accepts_declared_output_independent_feasibility_filter(tmp_path):
    model = {
        "slug": "m",
        "model_id": "m",
        "revision": "r",
        "local_dir": "m",
        "prompt_policy": "p",
    }
    old_config = {
        "matrix_version": "old",
        "artifact_suffix": "old",
        "task_count": 2,
        "models": [model],
    }
    new_config = {
        "matrix_version": "new",
        "artifact_suffix": "new",
        "task_count": 1,
        "models": [model],
        "feasibility_filter": {"decision_independent_of_model_outputs": True},
    }
    first = deepcopy(record()["tasks"][0])
    second = deepcopy(first)
    second["source_path"] = "b/problem0.bddl"
    second["source_sha256"] = "s2"
    old_record = record()
    old_record["tasks"] = [first, second]
    new_record = record()
    new_record["tasks"] = [deepcopy(first)]
    (tmp_path / "m_queue_2_sampling_old.json").write_text(
        __import__("json").dumps(old_record), encoding="utf-8"
    )
    (tmp_path / "m_queue_1_sampling_new.json").write_text(
        __import__("json").dumps(new_record), encoding="utf-8"
    )
    result = MODULE.analyze(old_config, new_config, tmp_path, tmp_path)
    assert result["overlap_task_count"] == 1
