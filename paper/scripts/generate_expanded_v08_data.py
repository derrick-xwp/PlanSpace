#!/usr/bin/env python3
"""Materialize Qwen3-8B structural macros from the six-model v0.8 run."""

from __future__ import annotations

import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


if __name__ == "__main__":
    sys.argv[1:] = [
        "--suffix",
        "v0_8_expanded_six",
        "--output",
        str(ROOT / "paper" / "generated_expanded_v08.tex"),
        *sys.argv[1:],
    ]
    from generate_expanded_coverage_data import main

    main()
