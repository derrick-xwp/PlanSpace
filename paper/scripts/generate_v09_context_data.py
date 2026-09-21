#!/usr/bin/env python3
"""Materialize manuscript macros from the six-model 171-task v0.9 matrix."""

from __future__ import annotations

import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


if __name__ == "__main__":
    sys.argv[1:] = [
        "--artifact-suffix",
        "v0_9_context171_six",
        "--task-count",
        "171",
        "--output-count",
        "5130",
        "--coverage",
        str(ROOT / "artifacts" / "bounded_family_coverage_v0_4.json"),
        "--output",
        str(ROOT / "paper" / "generated_v09_context.tex"),
        *sys.argv[1:],
    ]
    from generate_v02_data import main

    main()
