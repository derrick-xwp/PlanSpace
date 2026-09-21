#!/usr/bin/env python3
"""Freeze a shared-context subset and project completed larger-matrix runs.

The filter is model-output independent: a task is retained exactly when the
recorded tokenizer audit says the frozen chat plus the common generation
budget fits the smallest model context.  Original queue indices are preserved
so task/sample seeds remain identical to the parent run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from run_local_model_queue import render_table, summarize


ROOT = Path(__file__).resolve().parents[1]
PARENT_QUEUE = ROOT / "artifacts/action_semantics_supported_queue_173_v0_1.json"
PARENT_SPLIT = ROOT / "artifacts/structural_splits_173_v0_1.json"
PARENT_CONFIG = ROOT / "configs/model_matrix_v0_8_expanded_173_six_model_gpuhub.json"
CONTEXT_AUDIT = ROOT / "artifacts/prompt_context_compatibility_173_v0_1.json"
OUTPUT_QUEUE = ROOT / "artifacts/action_semantics_supported_queue_171_context_v0_1.json"
OUTPUT_SPLIT = ROOT / "artifacts/structural_splits_171_context_v0_1.json"
OUTPUT_CONFIG = ROOT / "configs/model_matrix_v0_9_context_171_six_model_gpuhub.json"

PARENT_SUFFIX = "v0_8_expanded_six"
OUTPUT_SUFFIX = "v0_9_context171_six"
OUTPUT_EVIDENCE_STATUS = (
    "v0_9_context_compatible_171_six_model_feasibility_filtered"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def freeze_queue(parent: dict, audit: dict) -> tuple[dict, list[str]]:
    audit_by_path = {row["source_path"]: row for row in audit["records"]}
    if set(audit_by_path) != {row["source_path"] for row in parent["records"]}:
        raise ValueError("context audit and parent queue task sets differ")
    retained = []
    excluded = []
    for original_task_index, row in enumerate(parent["records"]):
        audited = audit_by_path[row["source_path"]]
        if audited["source_sha256"] != row["source_sha256"]:
            raise ValueError(f"source hash mismatch: {row['source_path']}")
        if audited["fits_requested_budget"]:
            retained.append({**row, "original_task_index": original_task_index})
        else:
            excluded.append(row["source_path"])
    if len(retained) != audit["retained_count"] or len(excluded) != audit["excluded_count"]:
        raise ValueError("context audit counts are inconsistent")
    queue = {
        **{key: value for key, value in parent.items() if key != "records"},
        "evidence_status": "model_independent_context_feasibility_filtered",
        "queue_version": "planspace_action_semantics_supported_context171_v0.1",
        "selected_count": len(retained),
        "context_compatibility_audit": str(CONTEXT_AUDIT.relative_to(ROOT)),
        "context_compatibility_audit_sha256": sha256(CONTEXT_AUDIT),
        "parent_queue": str(PARENT_QUEUE.relative_to(ROOT)),
        "parent_queue_sha256": sha256(PARENT_QUEUE),
        "context_excluded_count": len(excluded),
        "context_excluded": excluded,
        "semantic_boundary": (
            parent["semantic_boundary"]
            + " The shared model matrix additionally excludes tasks whose frozen "
            "serialized chat plus 512-token output budget exceeds the smallest "
            "checkpoint context window; this filter does not inspect model outputs."
        ),
        "records": retained,
    }
    return queue, excluded


def freeze_split(parent: dict, retained_paths: set[str]) -> dict:
    records = [row for row in parent["records"] if row["source_path"] in retained_paths]
    if len(records) != len(retained_paths):
        raise ValueError("split manifest does not cover retained queue")
    return {
        **{key: value for key, value in parent.items() if key != "records"},
        "split_version": "planspace_structural_splits_context171_v0.1",
        "task_count": len(records),
        "parent_split_manifest": str(PARENT_SPLIT.relative_to(ROOT)),
        "parent_split_manifest_sha256": sha256(PARENT_SPLIT),
        "context_compatibility_audit": str(CONTEXT_AUDIT.relative_to(ROOT)),
        "records": records,
    }


def freeze_config(parent: dict, task_count: int) -> dict:
    config = {
        **parent,
        "matrix_version": "planspace_model_matrix_v0.9_context_171_six_model",
        "queue": str(OUTPUT_QUEUE.relative_to(ROOT)),
        "task_count": task_count,
        "split_manifest": str(OUTPUT_SPLIT.relative_to(ROOT)),
        "artifact_suffix": OUTPUT_SUFFIX,
        "evidence_status": OUTPUT_EVIDENCE_STATUS,
        "feasibility_filter": {
            "audit": str(CONTEXT_AUDIT.relative_to(ROOT)),
            "audit_sha256": sha256(CONTEXT_AUDIT),
            "rule": (
                "retain iff frozen serialized chat plus the shared 512-token output "
                "budget fits the minimum checkpoint context window"
            ),
            "decision_independent_of_model_outputs": True,
        },
    }
    return config


def project_completed_raw(
    slug: str, *, retained_paths: set[str], queue_version: str, artifacts: Path
) -> Path:
    source = artifacts / f"{slug}_queue_173_sampling_{PARENT_SUFFIX}.json"
    record = load(source)
    tasks = [task for task in record["tasks"] if task["source_path"] in retained_paths]
    if len(tasks) != len(retained_paths) or {t["source_path"] for t in tasks} != retained_paths:
        raise ValueError(f"incomplete projected task set: {source}")
    projected = {
        **{key: value for key, value in record.items() if key not in {"summary", "tasks"}},
        "evidence_status": OUTPUT_EVIDENCE_STATUS,
        "queue_version": queue_version,
        "derivation": {
            "type": "model_output_independent_context_feasibility_projection",
            "source_artifact": source.name,
            "source_sha256": sha256(source),
            "context_compatibility_audit": str(CONTEXT_AUDIT.relative_to(ROOT)),
            "context_compatibility_audit_sha256": sha256(CONTEXT_AUDIT),
            "regeneration": False,
        },
        "summary": summarize(tasks),
        "tasks": tasks,
    }
    output = artifacts / f"{slug}_queue_{len(tasks)}_sampling_{OUTPUT_SUFFIX}.json"
    table = artifacts / f"{slug}_queue_{len(tasks)}_sampling_{OUTPUT_SUFFIX}.md"
    write_json(output, projected)
    table.write_text(render_table(tasks), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts")
    parser.add_argument(
        "--project-slugs", nargs="*", default=["qwen3_4b", "phi4_mini", "mistral_7b"]
    )
    args = parser.parse_args()

    parent_queue = load(PARENT_QUEUE)
    audit = load(CONTEXT_AUDIT)
    queue, excluded = freeze_queue(parent_queue, audit)
    retained_paths = {row["source_path"] for row in queue["records"]}
    split = freeze_split(load(PARENT_SPLIT), retained_paths)
    config = freeze_config(load(PARENT_CONFIG), len(retained_paths))
    write_json(OUTPUT_QUEUE, queue)
    write_json(OUTPUT_SPLIT, split)
    write_json(OUTPUT_CONFIG, config)

    outputs = [
        project_completed_raw(
            slug,
            retained_paths=retained_paths,
            queue_version=queue["queue_version"],
            artifacts=args.artifacts,
        )
        for slug in args.project_slugs
    ]
    print(
        json.dumps(
            {
                "retained_count": len(retained_paths),
                "excluded": excluded,
                "queue": str(OUTPUT_QUEUE),
                "split": str(OUTPUT_SPLIT),
                "config": str(OUTPUT_CONFIG),
                "projected": [str(path) for path in outputs],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
