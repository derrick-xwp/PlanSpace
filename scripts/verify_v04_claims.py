#!/usr/bin/env python3
"""Fail closed on stale hand-written v0.2 results in the v0.4 manuscript."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "paper" / "main.tex"
GENERATED = ROOT / "paper" / "generated_v04.tex"


def section(text: str, name: str, next_name: str) -> str:
    start = text.index(name)
    end = text.index(next_name, start)
    return text[start:end]


def verify(manuscript: Path = MANUSCRIPT, generated: Path = GENERATED) -> None:
    source = manuscript.read_text(encoding="utf-8")
    macros = generated.read_text(encoding="utf-8")
    assert "from v0_4; do not edit." in macros
    assert r"\newcommand{\VTwoBehaviorGapModelCount}{5}" in macros
    assert r"\input{generated_v04.tex}" in source

    abstract = section(source, r"\begin{abstract}", r"\end{abstract}")
    results = section(source, r"\section{Results}", r"\section{Limitations}")
    assert r"\VTwoBehaviorGapModelCount{} of" in abstract
    assert "Every model with a valid output" not in abstract

    # Numerical experimental claims in these two high-risk sections must flow
    # through generated macros or tables.  This blocks the stale v0.2 prose
    # values that previously diverged from the frozen v0.4 artifacts.
    for block_name, block in (("abstract", abstract), ("results", results)):
        assert not re.search(r"\b\d+\.\d+\\%", block), (
            f"hand-written percentage in {block_name}; use a generated macro or table"
        )

    stale_phrases = (
        "from 25.8\\% to 85.4\\%",
        "from 11.4\\% to 62.2\\%",
        "gains 4.8 goal-validity points",
        "from 7.0\\% to 26.8\\%",
        "from 9\\% at one draw to 29\\% at five",
        "Mistral rises from 72\\% to 84\\%",
        "every model with a valid output exhibits a",
    )
    lowered = source.lower()
    assert all(phrase.lower() not in lowered for phrase in stale_phrases)


def main() -> None:
    verify()
    print("v0.4 manuscript claim audit verified")


if __name__ == "__main__":
    main()
