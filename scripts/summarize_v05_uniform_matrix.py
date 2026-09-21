#!/usr/bin/env python3
"""Create an auditable summary for the frozen v0.5 raw model matrix."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
SLUGS = ("qwen3_4b", "phi4_mini", "mistral_7b", "olmo2_7b", "qwen3_8b", "qwen3_14b")


def main() -> None:
    models = []
    for slug in SLUGS:
        path = ARTIFACTS / f"{slug}_queue_100_sampling_v0_5.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        if len(record.get("tasks", [])) != 100 or record["summary"].get("sample_count") != 500:
            raise ValueError(f"incomplete matrix artifact: {path}")
        models.append(
            {
                "slug": slug,
                "model_id": record["model_id"],
                "model_revision": record["model_revision"],
                "protocol_version": record["protocol_version"],
                "evidence_status": record.get("evidence_status"),
                "summary": record["summary"],
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    output = {
        "analysis_version": "planspace-v05-uniform-compact-raw-summary-v1",
        "task_count_per_model": 100,
        "samples_per_task": 5,
        "total_outputs": 3000,
        "models": models,
    }
    out = ARTIFACTS / "uniform_compact_matrix_summary_v0_5.json"
    out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
