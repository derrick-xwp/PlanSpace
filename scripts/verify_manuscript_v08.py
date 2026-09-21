#!/usr/bin/env python3
"""Fail closed on stale counts or overclaimed v0.8 manuscript statements."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    r"\input{generated_v08_expanded.tex}",
    r"\input{generated_expanded_v08.tex}",
    r"\input{generated_cross_run_v08.tex}",
    r"\input{results_v06_tables.tex}",
    r"\input{generated_prompt_effect.tex}",
    r"\PromptSerializationEffectTable",
    r"On \VTwoTaskCount{} compatibility-filtered BEHAVIOR-1K tasks",
    r"\VTwoTaskCount{}",
    r"\VTwoOutputsPerModel{}",
    r"\VTwoOutputCount{}",
    "173 tasks",
    "uniform compact",
    "compatibility-filtered",
    "rather than independent human annotators",
    "adversarial consistency check",
    "not a same-seed confirmatory experiment",
)

FORBIDDEN = (
    r"\input{generated_v06.tex}",
    r"\input{generated_expanded_v07.tex}",
    r"\input{generated_v04.tex}",
    r"\input{results_v04_tables.tex}",
    "Main v0.4 model matrix",
    "a same-seed, same-v0.4 paired rerun would be required",
    "the archived uniform-prompt v0.5 track uses a different",
    "The main v0.6 matrix",
    "main v0.6",
    "3,000 outputs",
)


def verify(text: str) -> None:
    missing = [phrase for phrase in REQUIRED if phrase not in text]
    stale = [phrase for phrase in FORBIDDEN if phrase in text]
    if missing:
        raise AssertionError("missing required v0.8 manuscript evidence: " + "; ".join(missing))
    if stale:
        raise AssertionError("stale primary-matrix manuscript claim remains: " + "; ".join(stale))
    lowered = text.lower()
    overclaims = (
        "human-validated",
        "validated by human",
        "simulator-validated",
        "physically feasible plans",
        "externally preregistered",
    )
    present = [phrase for phrase in overclaims if phrase in lowered]
    if present:
        raise AssertionError("unsupported validation claim: " + "; ".join(present))


def main() -> None:
    text = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    verify(text)
    print("v0.8 manuscript claims verified")


if __name__ == "__main__":
    main()
