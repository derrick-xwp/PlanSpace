#!/usr/bin/env python3
"""Compare overlapping tasks across two frozen six-model runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sample_metrics(sample: dict) -> dict[str, bool]:
    execution = sample.get("execution") or {}
    return {
        "parse": sample.get("parsed_plan") is not None and sample.get("parse_error") is None,
        "executable": bool(execution.get("executable")),
        "goal_valid": bool(execution.get("valid")),
        "exact": bool(sample.get("exact_match")),
    }


def rate(rows: list[dict], key: str) -> float:
    return sum(row[key] for row in rows) / len(rows)


def summarize_model(old: dict, new: dict, overlap_sources: set[str]) -> dict:
    if old["model_id"] != new["model_id"] or old["model_revision"] != new["model_revision"]:
        raise ValueError("model identity drift")
    if old["protocol_version"] != new["protocol_version"]:
        raise ValueError("protocol drift")
    if old["generic_domain_version"] != new["generic_domain_version"]:
        raise ValueError("generic-domain drift")
    if old["decoding"] != new["decoding"]:
        raise ValueError("decoding drift")

    old_by_source = {task["source_path"]: task for task in old["tasks"]}
    new_by_source = {task["source_path"]: task for task in new["tasks"]}
    if not overlap_sources <= set(old_by_source) or not overlap_sources <= set(new_by_source):
        raise ValueError("declared overlap is not present in both runs")

    old_metrics: list[dict] = []
    new_metrics: list[dict] = []
    identical_samples = 0
    matching_seeds = 0
    matching_prompts = 0
    matching_serialized_chats = 0
    all_outputs_equal_tasks = 0
    mismatched_output_sources = []
    for source in sorted(overlap_sources):
        left = old_by_source[source]
        right = new_by_source[source]
        if left["source_sha256"] != right["source_sha256"]:
            raise ValueError(f"source hash drift: {source}")
        matching_prompts += left["prompt_sha256"] == right["prompt_sha256"]
        matching_serialized_chats += (
            left["serialized_chat_sha256"] == right["serialized_chat_sha256"]
        )
        left_samples = {sample["sample_index"]: sample for sample in left["samples"]}
        right_samples = {sample["sample_index"]: sample for sample in right["samples"]}
        if set(left_samples) != set(right_samples):
            raise ValueError(f"sample-index drift: {source}")
        task_equal = True
        for index in sorted(left_samples):
            old_sample = left_samples[index]
            new_sample = right_samples[index]
            matching_seeds += old_sample["seed"] == new_sample["seed"]
            equal = old_sample["raw_output"] == new_sample["raw_output"]
            identical_samples += equal
            task_equal &= equal
            old_metrics.append(sample_metrics(old_sample))
            new_metrics.append(sample_metrics(new_sample))
        all_outputs_equal_tasks += task_equal
        if not task_equal:
            mismatched_output_sources.append(source)

    task_count = len(overlap_sources)
    sample_count = len(old_metrics)
    metrics = {}
    for key in ("parse", "executable", "goal_valid", "exact"):
        old_rate = rate(old_metrics, key)
        new_rate = rate(new_metrics, key)
        metrics[key] = {
            "old_rate": old_rate,
            "new_rate": new_rate,
            "new_minus_old": new_rate - old_rate,
        }
    return {
        "model_id": old["model_id"],
        "model_revision": old["model_revision"],
        "overlap_task_count": task_count,
        "overlap_sample_count": sample_count,
        "prompt_hash_match_task_count": matching_prompts,
        "serialized_chat_hash_match_task_count": matching_serialized_chats,
        "seed_match_sample_count": matching_seeds,
        "raw_output_match_sample_count": identical_samples,
        "all_samples_match_task_count": all_outputs_equal_tasks,
        "raw_output_match_rate": identical_samples / sample_count,
        "all_samples_match_task_rate": all_outputs_equal_tasks / task_count,
        "mismatched_output_sources": mismatched_output_sources,
        "metrics": metrics,
    }


def analyze(old_config: dict, new_config: dict, old_dir: Path, new_dir: Path) -> dict:
    old_models = {model["slug"]: model for model in old_config["models"]}
    new_models = {model["slug"]: model for model in new_config["models"]}
    identity_fields = ("model_id", "revision", "local_dir", "prompt_policy")
    old_identities = {
        slug: tuple(model.get(field) for field in identity_fields)
        for slug, model in old_models.items()
    }
    new_identities = {
        slug: tuple(model.get(field) for field in identity_fields)
        for slug, model in new_models.items()
    }
    if old_identities != new_identities:
        raise ValueError("model declarations differ across runs")
    # Historical configs predate the explicit task_count field and may carry
    # JSON null rather than omitting it.  Both forms mean the frozen 100-task
    # queue; do not let int(None) break the post-run audit.
    old_task_count = int(old_config.get("task_count") or 100)
    new_task_count = int(new_config.get("task_count") or 100)
    old_suffix = old_config["artifact_suffix"]
    new_suffix = new_config["artifact_suffix"]
    records = []
    overlap_sources: set[str] | None = None
    loaded = []
    for slug in old_models:
        old = load(old_dir / f"{slug}_queue_{old_task_count}_sampling_{old_suffix}.json")
        new = load(new_dir / f"{slug}_queue_{new_task_count}_sampling_{new_suffix}.json")
        sources = {task["source_path"] for task in old["tasks"]} & {
            task["source_path"] for task in new["tasks"]
        }
        overlap_sources = sources if overlap_sources is None else overlap_sources & sources
        loaded.append((old, new))
    if overlap_sources is None or not overlap_sources:
        raise ValueError("runs do not contain a non-empty shared task set")
    if len(overlap_sources) != old_task_count and not new_config.get("feasibility_filter"):
        raise ValueError(
            "new run must contain the complete old task set unless it declares "
            "a model-output-independent feasibility filter"
        )
    for old, new in loaded:
        records.append(summarize_model(old, new, overlap_sources))
    return {
        "schema_version": "planspace.cross_run_reproducibility.v0.1",
        "evidence_status": "posthoc_cross_run_diagnostic",
        "old_matrix_version": old_config["matrix_version"],
        "new_matrix_version": new_config["matrix_version"],
        "overlap_task_count": len(overlap_sources),
        "models": records,
        "interpretation_boundary": (
            "This diagnostic measures observed reproducibility across two archived runs. "
            "It is not a primary model comparison and does not alter the frozen metrics."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-config", type=Path, required=True)
    parser.add_argument("--new-config", type=Path, required=True)
    parser.add_argument("--old-dir", type=Path, required=True)
    parser.add_argument("--new-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(load(args.old_config), load(args.new_config), args.old_dir, args.new_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
