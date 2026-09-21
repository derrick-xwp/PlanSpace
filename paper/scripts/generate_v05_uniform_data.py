#!/usr/bin/env python3
"""Generate the archived v0.5 table from version-matched frozen artifacts."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
MODELS = [
    ("qwen3_4b", "Qwen3-4B"),
    ("phi4_mini", "Phi-4-mini"),
    ("mistral_7b", "Mistral-7B"),
    ("olmo2_7b", "OLMo-2-7B"),
    ("qwen3_8b", "Qwen3-8B"),
    ("qwen3_14b", "Qwen3-14B"),
]


def main() -> None:
    rows = []
    for slug, label in MODELS:
        path = ARTIFACTS / f"{slug}_queue_100_enriched_v0_5.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        summary = record["summary"]
        if len(record["tasks"]) != 100 or summary["sample_count"] != 500:
            raise ValueError(f"incomplete v0.5 artifact: {path}")
        if record["generic_domain_version"] != "planspace_generic_household_v0.1-candidate":
            raise ValueError(f"unexpected v0.5 action-domain version: {path}")
        rows.append(
            (label, *(100 * summary[key] for key in (
                "parse_success_rate",
                "executable_rate",
                "goal_valid_rate",
                "partial_order_match_rate",
                "exact_match_rate",
                "single_reference_false_rejection_among_valid",
            )))
        )

    best_goal = max(row[3] for row in rows)
    best_exact = max(row[5] for row in rows)

    lines = [
        "% Generated from the archived uniform-compact v0.5 six-model matrix.",
        r"\newcommand{\VFiveHistoricalTable}{%",
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Archived uniform-compact v0.5 track (\%). Every model uses the same compact prompt and contributes 500 outputs. This separate historical track uses the v0.1 action-domain and executor.}",
        r"\label{tab:v05-historical}",
        r"\small",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Model & Parse & Exec. & Goal & PO & Exact & FRR \\",
        r"\midrule",
    ]
    for label, parse, executable, goal, partial_order, exact, frr in rows:
        lines.append(
            f"{label} & {parse:.1f} & {executable:.1f} & {goal:.1f} & "
            f"{partial_order:.1f} & {exact:.1f} & {frr:.1f} " + r"\\"
        )
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}%",
        r"}",
        rf"\newcommand{{\VFiveHistoricalBestGoal}}{{{best_goal:.1f}\%}}",
        rf"\newcommand{{\VFiveHistoricalBestExact}}{{{best_exact:.1f}\%}}",
        r"\newcommand{\VFiveHistoricalTotalOutputs}{3,000}",
    ])
    (ROOT / "paper" / "generated_v05_uniform.tex").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
