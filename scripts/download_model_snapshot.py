#!/usr/bin/env python3
"""Download one immutable Hugging Face model snapshot and record a manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from huggingface_hub import snapshot_download


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_id")
    parser.add_argument("revision", help="Immutable Hugging Face commit SHA")
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--allow-pattern",
        action="append",
        default=None,
        help="Optional Hugging Face allow pattern; may be repeated.",
    )
    parser.add_argument(
        "--ignore-pattern",
        action="append",
        default=None,
        help="Optional Hugging Face ignore pattern; may be repeated.",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    resolved = Path(
        snapshot_download(
            repo_id=args.model_id,
            revision=args.revision,
            local_dir=args.output,
            allow_patterns=args.allow_pattern,
            ignore_patterns=args.ignore_pattern,
        )
    )
    weight_files = sorted(resolved.glob("*.safetensors"))
    manifest = {
        "model_id": args.model_id,
        "revision": args.revision,
        "resolved_path": str(resolved.resolve()),
        "allow_patterns": args.allow_pattern or [],
        "ignore_patterns": args.ignore_pattern or [],
        "weight_files": [
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in weight_files
        ],
    }
    manifest["weight_bytes_total"] = sum(
        item["bytes"] for item in manifest["weight_files"]
    )
    (resolved / "planspace_model_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
