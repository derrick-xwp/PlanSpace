import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "process_model_matrix_v0_2.py"
SPEC = importlib.util.spec_from_file_location("process_model_matrix_v02", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixtures():
    model = {"model_id": "model/a", "revision": "rev-a"}
    config = {
        "protocol_version": "protocol-v2",
        "generic_domain_version": "domain-v1",
        "decoding": {
            "samples_per_task": 5,
            "seed_base": 7,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_new_tokens": 512,
            "enable_thinking": False,
        },
    }
    expected = {f"task-{index}": f"source-{index}" for index in range(100)}
    tasks = [
        {
            "source_path": path,
            "source_sha256": source_hash,
            "prompt_sha256": f"prompt-{index}",
            "serialized_chat_sha256": f"chat-{index}",
            "samples": [{"sample_index": j} for j in range(5)],
        }
        for index, (path, source_hash) in enumerate(expected.items())
    ]
    record = {
        "model_id": model["model_id"],
        "model_revision": model["revision"],
        "protocol_version": config["protocol_version"],
        "generic_domain_version": config["generic_domain_version"],
        "decoding": dict(config["decoding"]),
        "tasks": tasks,
    }
    return record, model, config, expected


def validate(record, model, config, expected, common=None):
    common = {} if common is None else common
    MODULE.validate_raw_record(
        record, model, config, expected, common, path=Path("matrix.json")
    )
    return common


def test_validation_accepts_complete_frozen_matrix():
    record, model, config, expected = fixtures()
    common = validate(record, model, config, expected)
    assert len(common) == 100


def test_validation_accepts_configured_expanded_matrix():
    record, model, config, expected = fixtures()
    config["task_count"] = 99
    expected.pop("task-99")
    record["tasks"] = record["tasks"][:99]
    common = validate(record, model, config, expected)
    assert len(common) == 99


def test_validation_rejects_source_hash_drift():
    record, model, config, expected = fixtures()
    record["tasks"][0]["source_sha256"] = "changed"
    with pytest.raises(ValueError, match="source hash mismatch"):
        validate(record, model, config, expected)


def test_validation_rejects_evidence_status_drift_when_configured():
    record, model, config, expected = fixtures()
    config["evidence_status"] = "semantic-v0.4-complete"
    record["evidence_status"] = "old-or-unreviewed"
    with pytest.raises(ValueError, match="evidence-status mismatch"):
        validate(record, model, config, expected)


def test_validation_rejects_cross_model_prompt_drift():
    record, model, config, expected = fixtures()
    common = validate(record, model, config, expected)
    record["model_id"] = model["model_id"] = "model/b"
    record["model_revision"] = model["revision"] = "rev-b"
    record["tasks"][0]["prompt_sha256"] = "changed"
    with pytest.raises(ValueError, match="cross-model prompt hash mismatch"):
        validate(record, model, config, expected, common)


def test_validation_accepts_and_enforces_uniform_compact_prompt_track():
    record, model, config, expected = fixtures()
    model["prompt_policy"] = "uniform_compact_action_catalog_v1"
    record["prompt_template_policy"] = "uniform_compact_action_catalog_v1"
    for task in record["tasks"]:
        task["prompt_template"] = "uniform_compact_action_catalog_v1"
    common = validate(record, model, config, expected)
    assert len(common) == 100
    record["tasks"][0]["prompt_template"] = "canonical_full_catalog"
    with pytest.raises(ValueError, match="uniform compact template mismatch"):
        validate(record, model, config, expected)


def test_validation_rejects_task_set_drift():
    record, model, config, expected = fixtures()
    record["tasks"][0]["source_path"] = record["tasks"][1]["source_path"]
    with pytest.raises(ValueError, match="task-set mismatch"):
        validate(record, model, config, expected)


def test_reuse_validation_checks_every_json_identity(tmp_path):
    model = {"model_id": "model/a", "revision": "rev-a"}
    paths = []
    for name in ("enriched.json", "analysis.json", "analysis.md", "prefix.json", "catalog.json"):
        path = tmp_path / name
        if path.suffix == ".json":
            path.write_text(
                '{"model_id":"model/a","model_revision":"rev-a"}', encoding="utf-8"
            )
        else:
            path.write_text("table\n", encoding="utf-8")
        paths.append(path)
    MODULE.validate_reused_artifacts(model, tuple(paths))
    paths[-1].write_text(
        '{"model_id":"model/b","model_revision":"rev-a"}', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="model mismatch"):
        MODULE.validate_reused_artifacts(model, tuple(paths))
