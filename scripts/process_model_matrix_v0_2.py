#!/usr/bin/env python3
"""Validate and post-process every model in a frozen PlanSpace matrix.

The filename is retained for backwards compatibility with the v0.2 release
tooling.  Artifact naming and evidence identity come from the supplied config,
so the same fail-closed implementation also handles the semantic v0.4 rerun.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def run(command: list[str], *, repo_root: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    subprocess.run(command, cwd=repo_root, env=env, check=True)


def validate_raw_record(
    record: dict,
    model: dict,
    config: dict,
    expected_sources: dict[str, str],
    common_prompt_hashes: dict[str, str],
    *,
    path: Path,
) -> None:
    task_count = int(config.get("task_count", 100))
    samples_per_task = int(config["decoding"]["samples_per_task"])
    if record["model_id"] != model["model_id"] or record["model_revision"] != model["revision"]:
        raise ValueError(f"model identity mismatch: {path}")
    if record["protocol_version"] != config["protocol_version"]:
        raise ValueError(f"protocol mismatch: {path}")
    if record["generic_domain_version"] != config["generic_domain_version"]:
        raise ValueError(f"generic-domain mismatch: {path}")
    expected_evidence_status = config.get("evidence_status")
    if expected_evidence_status and record.get("evidence_status") != expected_evidence_status:
        raise ValueError(f"evidence-status mismatch: {path}")
    if record["decoding"] != {
        "samples_per_task": config["decoding"]["samples_per_task"],
        "seed_base": config["decoding"]["seed_base"],
        "temperature": config["decoding"]["temperature"],
        "top_p": config["decoding"]["top_p"],
        "max_new_tokens": config["decoding"]["max_new_tokens"],
        "enable_thinking": config["decoding"]["enable_thinking"],
    }:
        raise ValueError(f"decoding mismatch: {path}")
    tasks = record.get("tasks", [])
    if len(tasks) != task_count or any(
        len(task.get("samples", [])) != samples_per_task for task in tasks
    ):
        raise ValueError(f"incomplete matrix: {path}")
    observed_paths = [task.get("source_path") for task in tasks]
    if len(set(observed_paths)) != len(observed_paths) or set(observed_paths) != set(expected_sources):
        raise ValueError(f"task-set mismatch: {path}")
    for task in tasks:
        source_path = task["source_path"]
        if task.get("source_sha256") != expected_sources[source_path]:
            raise ValueError(f"source hash mismatch for {source_path}: {path}")
        prompt_hash = task.get("prompt_sha256")
        serialized_hash = task.get("serialized_chat_sha256")
        if not prompt_hash or not serialized_hash:
            raise ValueError(f"missing prompt or serialized-chat hash for {source_path}: {path}")
        prompt_policy = model.get("prompt_policy", "canonical_full_catalog")
        if prompt_policy == "canonical_full_catalog":
            if source_path in common_prompt_hashes and common_prompt_hashes[source_path] != prompt_hash:
                raise ValueError(f"cross-model prompt hash mismatch for {source_path}: {path}")
            common_prompt_hashes.setdefault(source_path, prompt_hash)
        elif prompt_policy == "context_fit_compact_action_catalog_v1":
            if record.get("context_fit_policy") != "compact_action_catalog_then_clamp_generation":
                raise ValueError(f"context-fit policy mismatch: {path}")
            template = task.get("prompt_template", "canonical_full_catalog")
            if template not in {"canonical_full_catalog", "context_fit_compact_action_catalog_v1"}:
                raise ValueError(f"unknown context-fit prompt template for {source_path}: {path}")
        elif prompt_policy == "uniform_compact_action_catalog_v1":
            if record.get("prompt_template_policy") != prompt_policy:
                raise ValueError(f"uniform compact policy mismatch: {path}")
            if task.get("prompt_template") != prompt_policy:
                raise ValueError(f"uniform compact template mismatch for {source_path}: {path}")
            if source_path in common_prompt_hashes and common_prompt_hashes[source_path] != prompt_hash:
                raise ValueError(f"cross-model compact prompt hash mismatch for {source_path}: {path}")
            common_prompt_hashes.setdefault(source_path, prompt_hash)
        else:
            raise ValueError(f"unknown prompt policy for {path}: {prompt_policy}")


def validate_reused_artifacts(model: dict, paths: tuple[Path, ...]) -> None:
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "missing reused per-model artifacts: " + ", ".join(map(str, missing))
        )
    for path in paths:
        if path.suffix != ".json":
            continue
        item = json.loads(path.read_text(encoding="utf-8"))
        if item.get("model_id") != model["model_id"]:
            raise ValueError(f"reused artifact model mismatch: {path}")
        if item.get("model_revision") != model["revision"]:
            raise ValueError(f"reused artifact revision mismatch: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("result_dir", type=Path)
    parser.add_argument(
        "--source-root",
        type=Path,
        help="override the machine-specific source_root recorded in the config",
    )
    parser.add_argument(
        "--reuse-per-model",
        action="store_true",
        help=(
            "reuse already generated enriched, analysis, and sensitivity files; "
            "only validate and assemble cross-model artifacts"
        ),
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    config = json.loads(args.config.read_text(encoding="utf-8"))
    artifact_suffix = config.get("artifact_suffix", "v0_2")
    task_count = int(config.get("task_count", 100))
    source_root = args.source_root or Path(config["source_root"])
    analysis_domain_audit = repo_root / config.get(
        "analysis_domain_audit",
        f"artifacts/generic_domain_audit_100_{artifact_suffix}.json",
    )
    queue = json.loads((repo_root / config["queue"]).read_text(encoding="utf-8"))
    expected_sources = {
        row["source_path"]: row["source_sha256"] for row in queue["records"]
    }
    if len(expected_sources) != task_count:
        raise ValueError(
            f"frozen matrix queue must contain exactly {task_count} unique source paths"
        )
    common_prompt_hashes: dict[str, str] = {}
    enriched_paths = []
    sensitivity_rows = []
    catalog_projection_rows = []
    for model in config["models"]:
        slug = model["slug"]
        raw = args.result_dir / f"{slug}_queue_{task_count}_sampling_{artifact_suffix}.json"
        if not raw.is_file():
            raise FileNotFoundError(raw)
        record = json.loads(raw.read_text(encoding="utf-8"))
        validate_raw_record(
            record,
            model,
            config,
            expected_sources,
            common_prompt_hashes,
            path=raw,
        )

        enriched = args.result_dir / f"{slug}_queue_{task_count}_enriched_{artifact_suffix}.json"
        analysis = args.result_dir / f"{slug}_queue_{task_count}_analysis_{artifact_suffix}.json"
        analysis_md = args.result_dir / f"{slug}_queue_{task_count}_analysis_{artifact_suffix}.md"
        sensitivity = args.result_dir / f"{slug}_action_prefix_sensitivity_{artifact_suffix}.json"
        catalog_projection = (
            args.result_dir / f"{slug}_catalog_projection_sensitivity_{artifact_suffix}_posthoc.json"
        )
        if args.reuse_per_model:
            required = (enriched, analysis, analysis_md, sensitivity, catalog_projection)
            validate_reused_artifacts(model, required)
        else:
            run(
                [
                    sys.executable,
                    str(repo_root / "scripts/enrich_partial_order_metrics.py"),
                    str(raw),
                    str(source_root),
                    "--output",
                    str(enriched),
                    "--generic-domain-version",
                    config["generic_domain_version"],
                ],
                repo_root=repo_root,
            )
            run(
                [
                    sys.executable,
                    str(repo_root / "scripts/analyze_model_queue.py"),
                    str(enriched),
                    str(analysis_domain_audit),
                    "--split-manifest",
                    str(
                        repo_root
                        / config.get(
                            "split_manifest",
                            "artifacts/structural_splits_100_v0_1.json",
                        )
                    ),
                    "--output",
                    str(analysis),
                    "--table-output",
                    str(analysis_md),
                ],
                repo_root=repo_root,
            )
            run(
                [
                    sys.executable,
                    str(repo_root / "scripts/analyze_action_prefix_sensitivity.py"),
                    str(raw),
                    str(source_root),
                    "--output",
                    str(sensitivity),
                    "--generic-domain-version",
                    config["generic_domain_version"],
                ],
                repo_root=repo_root,
            )
            run(
                [
                    sys.executable,
                    str(repo_root / "scripts/analyze_catalog_projection_sensitivity.py"),
                    str(raw),
                    str(source_root),
                    "--output",
                    str(catalog_projection),
                    "--generic-domain-version",
                    config["generic_domain_version"],
                ],
                repo_root=repo_root,
            )
        enriched_paths.append(enriched)
        sensitivity_rows.append(
            {
                "model_id": model["model_id"],
                "model_revision": model["revision"],
                **json.loads(sensitivity.read_text(encoding="utf-8"))["summary"],
            }
        )
        catalog_projection_rows.append(
            {
                "model_id": model["model_id"],
                "model_revision": model["revision"],
                **json.loads(catalog_projection.read_text(encoding="utf-8"))["summary"],
            }
        )

    comparison = args.result_dir / f"multi_model_comparison_{artifact_suffix}.json"
    comparison_md = args.result_dir / f"multi_model_comparison_{artifact_suffix}.md"
    run(
        [
            sys.executable,
            str(repo_root / "scripts/compare_model_matrix.py"),
            *map(str, enriched_paths),
            "--output",
            str(comparison),
            "--table-output",
            str(comparison_md),
        ],
        repo_root=repo_root,
    )
    sampling = args.result_dir / f"sampling_curve_analysis_{artifact_suffix}.json"
    sampling_md = args.result_dir / f"sampling_curve_analysis_{artifact_suffix}.md"
    run(
        [
            sys.executable,
            str(repo_root / "scripts/analyze_sampling_curve.py"),
            *map(str, enriched_paths),
            "--output",
            str(sampling),
            "--table-output",
            str(sampling_md),
        ],
        repo_root=repo_root,
    )

    sensitivity_summary = {
        "analysis_version": f"planspace-action-prefix-sensitivity-comparison-{artifact_suffix}",
        "rule": "remove one literal action_id= prefix from each JSON plan string; no other repair",
        "models": sensitivity_rows,
    }
    summary_json = args.result_dir / f"action_prefix_sensitivity_comparison_{artifact_suffix}.json"
    summary_json.write_text(json.dumps(sensitivity_summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Strict-interface sensitivity",
        "",
        "| Model | Strict parse | Normalized parse | Strict goal | Normalized goal | Strict exact | Normalized exact | Recovered valid |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sensitivity_rows:
        lines.append(
            f"| {row['model_id']} | {row['strict_parse_rate']:.2%} | "
            f"{row['normalized_parse_rate']:.2%} | {row['strict_goal_valid_rate']:.2%} | "
            f"{row['normalized_goal_valid_rate']:.2%} | {row['strict_exact_match_rate']:.2%} | "
            f"{row['normalized_exact_match_rate']:.2%} | {row['newly_recovered_valid_count']} |"
        )
    (args.result_dir / f"action_prefix_sensitivity_comparison_{artifact_suffix}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    catalog_summary = {
        "evidence_status": "posthoc_exploratory_interface_sensitivity",
        "analysis_version": "planspace-exact-catalog-projection-comparison-v0.1",
        "rule": (
            "accept an exact action id, its literal action_id= form, or an exact catalog "
            "record rendered in the prompt; no splitting, fuzzy matching, or JSON repair"
        ),
        "models": catalog_projection_rows,
    }
    catalog_json = args.result_dir / f"catalog_projection_sensitivity_comparison_{artifact_suffix}_posthoc.json"
    catalog_json.write_text(json.dumps(catalog_summary, indent=2) + "\n", encoding="utf-8")
    catalog_lines = [
        "# Post-hoc exact catalog-record projection sensitivity",
        "",
        "This analysis is exploratory because the rule was specified after early OLMo outputs were inspected.",
        "",
        "| Model | Strict parse | Projected parse | Strict goal | Projected goal | Strict exact | Projected exact | Recovered valid |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in catalog_projection_rows:
        catalog_lines.append(
            f"| {row['model_id']} | {row['strict_parse_rate']:.2%} | "
            f"{row['projected_parse_rate']:.2%} | {row['strict_goal_valid_rate']:.2%} | "
            f"{row['projected_goal_valid_rate']:.2%} | {row['strict_exact_match_rate']:.2%} | "
            f"{row['projected_exact_match_rate']:.2%} | {row['newly_recovered_valid_count']} |"
        )
    (args.result_dir / f"catalog_projection_sensitivity_comparison_{artifact_suffix}_posthoc.md").write_text(
        "\n".join(catalog_lines) + "\n", encoding="utf-8"
    )
    print(f"processed {len(enriched_paths)} complete model matrices")


if __name__ == "__main__":
    main()
