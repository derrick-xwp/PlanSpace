#!/usr/bin/env python3
"""Select tasks whose frozen model outputs reached the generation-token cap."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("model_results", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    model = json.loads(args.model_results.read_text(encoding="utf-8"))
    cap = model["decoding"]["max_new_tokens"]
    selected_paths = {
        task["source_path"]
        for task in model["tasks"]
        if any(
            sample["parse_error"] is not None
            and sample["generated_tokens"] >= cap
            for sample in task["samples"]
        )
    }
    records = [
        {**record, "original_task_index": index}
        for index, record in enumerate(queue["records"])
        if record["source_path"] in selected_paths
    ]
    if {record["source_path"] for record in records} != selected_paths:
        raise ValueError("model and queue task paths differ")
    report = {
        **{key: value for key, value in queue.items() if key != "records"},
        "queue_version": queue["queue_version"] + "-truncation-retry-v0.1",
        "selection_model_id": model["model_id"],
        "selection_model_revision": model["model_revision"],
        "selection_max_new_tokens": cap,
        "selected_count": len(records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selected_count": len(records), "paths": sorted(selected_paths)}, indent=2))


if __name__ == "__main__":
    main()
