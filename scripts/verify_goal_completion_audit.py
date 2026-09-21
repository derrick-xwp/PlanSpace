#!/usr/bin/env python3
"""Require the packaged completion audit to describe a genuinely final release."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INCOMPLETE_MARKERS = (
    "**Running.",
    "**Queued.",
    "**Pending",
    "remains in progress",
    "not yet complete",
)
REQUIRED_EVIDENCE = (
    "verify_v06_release.py --require-paper-data",
    "verify_prompt_serialization_effect.py --require-paper-data",
    "verify_v07_expanded_release.py --require-paper-data",
    "verify_output_validity_audit.py",
    "verify_manuscript_v06.py",
    "build_iclr_submission_package.py --matrix-version v0_6",
    "build_iclr_artifact_package.py",
)


def verify(text: str) -> None:
    incomplete = [marker for marker in INCOMPLETE_MARKERS if marker in text]
    if incomplete:
        raise AssertionError("completion audit still declares incomplete work: " + "; ".join(incomplete))
    missing = [item for item in REQUIRED_EVIDENCE if item not in text]
    if missing:
        raise AssertionError("completion audit omits required evidence: " + "; ".join(missing))
    if "goal is complete" not in text.lower():
        raise AssertionError("completion audit has no explicit final conclusion")


def main() -> None:
    path = ROOT / "docs" / "GOAL_COMPLETION_AUDIT.md"
    verify(path.read_text(encoding="utf-8"))
    print("goal-completion audit verified")


if __name__ == "__main__":
    main()
