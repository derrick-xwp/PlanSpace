#!/usr/bin/env python3
"""Materialize manuscript macros from the six-model 173-task v0.8 matrix."""

from __future__ import annotations

import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


if __name__ == "__main__":
    sys.argv[1:] = [
        "--artifact-suffix",
        "v0_8_expanded_six",
        "--task-count",
        "173",
        "--output-count",
        "5190",
        "--coverage",
        str(ROOT / "artifacts" / "bounded_family_coverage_v0_4.json"),
        "--output",
        str(ROOT / "paper" / "generated_v08_expanded.tex"),
        *sys.argv[1:],
    ]
    from generate_v02_data import main

    main()
