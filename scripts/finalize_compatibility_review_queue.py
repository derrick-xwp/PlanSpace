"""Freeze exactly 100 translation-passing instances for semantic review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from planspace.compatibility import finalize_review_queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("screen", type=Path)
    parser.add_argument("translation_audit", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-count", type=int, default=100)
    args = parser.parse_args()

    screen = json.loads(args.screen.read_text(encoding="utf-8"))
    audit = json.loads(args.translation_audit.read_text(encoding="utf-8"))
    report = finalize_review_queue(screen, audit, target_count=args.target_count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
