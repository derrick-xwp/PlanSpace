#!/usr/bin/env python3
"""Fail closed on stale counts or overclaimed v0.9 manuscript statements."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    r"\input{generated_v09_context.tex}",
    r"\input{generated_expanded_v09.tex}",
    r"\input{generated_cross_run_v09.tex}",
    r"\input{generated_revision_audits.tex}",
    r"\input{results_v06_tables.tex}",
    r"\input{generated_prompt_effect.tex}",
    r"\PromptSerializationEffectTable",
    r"\VTwoTaskCount{}",
    r"\VTwoOutputsPerModel{}",
    r"\VTwoOutputCount{}",
    "shared-context",
    "model-output-independent",
    "uniform compact",
    "Blinded internal AI-assisted judgments on 120 stratified archived outputs",
    "not independent human or simulator\nvalidation.",
    "This separate discovery procedure uses the same frozen\ntransition function $T_v$ as the evaluator.",
    "The archived comparisons include hardware and seed differences and measure",
)

FORBIDDEN = (
    r"\input{generated_v08_expanded.tex}",
    r"\input{generated_expanded_v08.tex}",
    r"\input{generated_cross_run_v08.tex}",
    r"\input{generated_v06.tex}",
    r"\input{generated_expanded_v07.tex}",
    "3,000 outputs",
    "5,190 outputs",
    "173-task expansion",
    "all 100 overlapping tasks",
    "The final suite contains \\GoalPlanRepresentativeCount{}",
)


def verify(text: str) -> None:
    missing = [phrase for phrase in REQUIRED if phrase not in text]
    stale = [phrase for phrase in FORBIDDEN if phrase in text]
    if missing:
        raise AssertionError("missing required v0.9 manuscript evidence: " + "; ".join(missing))
    if stale:
        raise AssertionError("stale primary-matrix manuscript claim remains: " + "; ".join(stale))
    lowered = text.lower()
    overclaims = (
        "human-validated",
        "validated by human",
        "physically feasible plans",
        "externally preregistered",
    )
    present = [phrase for phrase in overclaims if phrase in lowered]
    if present:
        raise AssertionError("unsupported validation claim: " + "; ".join(present))


def main() -> None:
    text = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    verify(text)
    print("v0.9 manuscript claims verified")


if __name__ == "__main__":
    main()
