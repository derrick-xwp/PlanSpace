#!/usr/bin/env python3
"""Run selected frozen model-matrix entries sequentially and resumably."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("models_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--slugs",
        nargs="+",
        help="Optional ordered subset of model slugs; defaults to config order.",
    )
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    by_slug = {model["slug"]: model for model in config["models"]}
    slugs = args.slugs or [model["slug"] for model in config["models"]]
    unknown = [slug for slug in slugs if slug not in by_slug]
    if unknown:
        raise ValueError(f"unknown model slugs: {unknown}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[1]
    queue = repo_root / config["queue"]
    decoding = config["decoding"]
    artifact_suffix = config.get("artifact_suffix", "v0_2")
    task_count = int(config.get("task_count", 100))
    for slug in slugs:
        model = by_slug[slug]
        model_path = args.models_root / model["local_dir"]
        if not model_path.is_dir():
            raise FileNotFoundError(f"model snapshot is missing: {model_path}")
        command = [
            sys.executable,
            str(repo_root / "scripts/run_local_model_queue.py"),
            str(queue),
            config["source_root"],
            "--model-path",
            str(model_path),
            "--model-id",
            model["model_id"],
            "--model-revision",
            model["revision"],
            "--protocol-version",
            config["protocol_version"],
            "--generic-domain-version",
            config["generic_domain_version"],
            "--evidence-status",
            config.get(
                "evidence_status",
                "candidate_100_task_model_run_pending_semantic_review",
            ),
            "--output",
            str(args.output_dir / f"{slug}_queue_{task_count}_sampling_{artifact_suffix}.json"),
            "--table-output",
            str(args.output_dir / f"{slug}_queue_{task_count}_sampling_{artifact_suffix}.md"),
            "--samples",
            str(decoding["samples_per_task"]),
            "--seed",
            str(decoding["seed_base"]),
            "--temperature",
            str(decoding["temperature"]),
            "--top-p",
            str(decoding["top_p"]),
            "--max-new-tokens",
            str(decoding["max_new_tokens"]),
        ]
        prompt_template = model.get(
            "prompt_template", config.get("prompt_template", "canonical_full_catalog")
        )
        command.extend(["--prompt-template", prompt_template])
        if model.get("fit_context", config.get("fit_context", False)):
            command.append("--fit-context")
        print(f"starting {slug}: {model['model_id']}@{model['revision']}", flush=True)
        subprocess.run(command, cwd=repo_root, check=True)


if __name__ == "__main__":
    main()
