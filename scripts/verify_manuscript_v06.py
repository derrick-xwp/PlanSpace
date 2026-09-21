#!/usr/bin/env python3
"""Fail closed on stale or overclaimed v0.6 manuscript statements."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    r"\input{generated_v06.tex}",
    r"\input{results_v06_tables.tex}",
    r"\input{generated_prompt_effect.tex}",
    r"\input{generated_expanded_v07.tex}",
    r"\PromptSerializationEffectTable",
    r"\ExpandedCoverageTable",
    "uniform compact",
    "compatibility-filtered",
    "rather than independent human annotators",
    "adversarial consistency check",
)

FORBIDDEN = (
    r"\input{generated_v04.tex}",
    r"\input{results_v04_tables.tex}",
    "Main v0.4 model matrix",
    "a same-seed, same-v0.4 paired rerun would be required",
    "the archived uniform-prompt v0.5 track uses a different",
)


def verify(text: str) -> None:
    missing = [phrase for phrase in REQUIRED if phrase not in text]
    stale = [phrase for phrase in FORBIDDEN if phrase in text]
    if missing:
        raise AssertionError("missing required v0.6 manuscript evidence: " + "; ".join(missing))
    if stale:
        raise AssertionError("stale v0.4 manuscript claim remains: " + "; ".join(stale))
    lowered = text.lower()
    overclaims = (
        "human-validated",
        "validated by human",
        "simulator-validated",
        "physically feasible plans",
    )
    present = [phrase for phrase in overclaims if phrase in lowered]
    if present:
        raise AssertionError("unsupported validation claim: " + "; ".join(present))


def main() -> None:
    text = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    verify(text)
    print("v0.6 manuscript claims verified")


if __name__ == "__main__":
    main()
