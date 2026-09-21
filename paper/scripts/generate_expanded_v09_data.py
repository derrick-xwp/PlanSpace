#!/usr/bin/env python3
"""Materialize structural macros from the six-model v0.9 context-compatible run."""

from __future__ import annotations

import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


if __name__ == "__main__":
    sys.argv[1:] = [
        "--suffix",
        "v0_9_context171_six",
        "--task-count",
        "171",
        "--queue",
        str(ROOT / "artifacts" / "action_semantics_supported_queue_171_context_v0_1.json"),
        "--output",
        str(ROOT / "paper" / "generated_expanded_v09.tex"),
        *sys.argv[1:],
    ]
    from generate_expanded_coverage_data import main

    main()
