#!/usr/bin/env python3
"""Generate fail-closed LaTeX rows from the complete six-model v0.2 matrix."""

from __future__ import annotations

import argparse
import json
import itertools
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
PAPER = ROOT / "paper"

MODEL_SPECS = [
    ("Qwen/Qwen3-4B", "Qwen3-4B", "qwen3_4b"),
    ("Qwen/Qwen3-8B", "Qwen3-8B", "qwen3_8b"),
    ("Qwen/Qwen3-14B", "Qwen3-14B", "qwen3_14b"),
    ("mistralai/Mistral-7B-Instruct-v0.3", "Mistral-7B", "mistral_7b"),
    ("allenai/OLMo-2-1124-7B-Instruct", "OLMo-2-7B", "olmo2_7b"),
    ("microsoft/Phi-4-mini-instruct", "Phi-4-mini", "phi4_mini"),
]

PAIR_LABELS = {
    "Qwen/Qwen3-4B": "Q3-4B",
    "Qwen/Qwen3-8B": "Q3-8B",
    "Qwen/Qwen3-14B": "Q3-14B",
    "mistralai/Mistral-7B-Instruct-v0.3": "Mistral",
    "allenai/OLMo-2-1124-7B-Instruct": "OLMo",
    "microsoft/Phi-4-mini-instruct": "Phi",
}

SELECTED_PAIRS = (
    ("Qwen/Qwen3-4B", "Qwen/Qwen3-8B"),
    ("Qwen/Qwen3-8B", "Qwen/Qwen3-14B"),
    ("Qwen/Qwen3-4B", "Qwen/Qwen3-14B"),
    ("mistralai/Mistral-7B-Instruct-v0.3", "allenai/OLMo-2-1124-7B-Instruct"),
)


def pct(value: float) -> str:
    return f"{100 * value:.1f}"


def pvalue(value: float) -> str:
    return "$<10^{-4}$" if value < 0.0001 else f"{value:.4f}"


def effect_ci(item: dict) -> str:
    return (
        f"{100 * item['estimate']:+.1f} "
        f"[{100 * item['ci95_low']:+.1f}, {100 * item['ci95_high']:+.1f}]"
    )


def rate_ci(item: dict) -> str:
    return (
        f"{100 * item['estimate']:.1f} "
        f"[{100 * item['ci95_low']:.1f}, {100 * item['ci95_high']:.1f}]"
    )


def orient_pair(pair: dict, left: str, right: str) -> dict:
    if pair["left_model"] == left and pair["right_model"] == right:
        return pair["metric_differences"]
    if pair["left_model"] != right or pair["right_model"] != left:
        raise ValueError(f"pair does not match requested orientation: {left}, {right}")
    output = {}
    for name, metric in pair["metric_differences"].items():
        output[name] = {
            **metric,
            "estimate": -metric["estimate"],
            "ci95_low": -metric["ci95_high"],
            "ci95_high": -metric["ci95_low"],
        }
    return output


def pair_row(left: str, right: str, metrics: dict) -> str:
    goal = metrics["goal_valid"]
    partial_order = metrics["partial_order"]
    exact = metrics["exact"]
    return (
        f"{PAIR_LABELS[left]} $-$ {PAIR_LABELS[right]} & "
        f"{effect_ci(exact)} & {pvalue(exact['holm_adjusted_p_value'])} & "
        f"{effect_ci(partial_order)} & {pvalue(partial_order['holm_adjusted_p_value'])} & "
        f"{effect_ci(goal)} & {pvalue(goal['holm_adjusted_p_value'])} \\\\"
    )


def render(
    comparison: dict,
    sensitivity: dict,
    catalog_projection: dict,
    analyses: dict,
    selection: dict,
    coverage: dict,
    *,
    task_count: int = 100,
    output_count: int = 3000,
) -> str:
    if task_count <= 0:
        raise ValueError("task count must be positive")
    if output_count % (len(MODEL_SPECS) * task_count) != 0:
        raise ValueError("output count must equal models x tasks x integer samples")
    outputs_per_model = output_count // len(MODEL_SPECS)
    samples_per_task = outputs_per_model // task_count
    expected = {model_id for model_id, _, _ in MODEL_SPECS}
    ordered_model_ids = [model_id for model_id, _, _ in MODEL_SPECS]
    if set(comparison.get("aggregate", {})) != expected:
        raise ValueError("six-model aggregate is incomplete or contains unexpected models")
    sensitivity_by_model = {row["model_id"]: row for row in sensitivity.get("models", [])}
    if set(sensitivity_by_model) != expected:
        raise ValueError("six-model interface sensitivity is incomplete")
    catalog_by_model = {
        row["model_id"]: row for row in catalog_projection.get("models", [])
    }
    if (
        catalog_projection.get("evidence_status")
        != "posthoc_exploratory_interface_sensitivity"
        or set(catalog_by_model) != expected
    ):
        raise ValueError("six-model post-hoc catalog projection is incomplete")
    if set(analyses) != expected:
        raise ValueError("six-model per-model analyses are incomplete")
    pairs = comparison.get("paired_comparisons", [])
    if len(pairs) != 15:
        raise ValueError("six models require exactly 15 pairwise comparisons")
    expected_pairs = {
        frozenset(pair) for pair in itertools.combinations(expected, 2)
    }
    actual_pairs = {
        frozenset((pair.get("left_model"), pair.get("right_model")))
        for pair in pairs
    }
    if actual_pairs != expected_pairs:
        raise ValueError("pairwise comparisons are duplicated, missing, or unexpected")
    for pair in pairs:
        metrics = pair.get("metric_differences", {})
        if set(metrics) != {"exact", "partial_order", "goal_valid"}:
            raise ValueError("each pair must contain exact, partial-order, and goal metrics")
        if any("holm_adjusted_p_value" not in item for item in metrics.values()):
            raise ValueError("each pairwise metric must contain a Holm-adjusted p-value")

    lines = [
        "% Generated by paper/scripts/generate_v02_data.py; do not edit.",
        r"\newcommand{\VTwoModelCount}{6}",
        r"\newcommand{\VTwoTaskCount}{%s}" % f"{task_count:,}",
        r"\newcommand{\VTwoSamplesPerTask}{%s}" % f"{samples_per_task:,}",
        r"\newcommand{\VTwoOutputsPerModel}{%s}" % f"{outputs_per_model:,}",
        r"\newcommand{\VTwoOutputCount}{%s}" % f"{output_count:,}",
        r"\newcommand{\SelectionSourceCount}{%d}" % selection["funnel"][0]["count"],
        r"\newcommand{\SelectionEligibleCount}{%d}" % selection["funnel"][1]["count"],
        r"\newcommand{\SelectionBufferCount}{%d}" % selection["funnel"][2]["count"],
        r"\newcommand{\SelectionTranslationCount}{%d}" % selection["funnel"][3]["count"],
        r"\newcommand{\SelectionFinalCount}{%d}" % selection["funnel"][4]["count"],
        r"\newcommand{\BoundedCoverageTaskCount}{%d}"
        % coverage["summary"]["exhaustively_analyzed_task_count"],
        r"\newcommand{\BoundedCoverageRate}{%s}"
        % pct(coverage["summary"]["micro_bounded_family_coverage"]),
    ]

    display_labels = {model_id: label for model_id, label, _ in MODEL_SPECS}
    for metric, macro in (
        ("goal_valid", "Goal"),
        ("partial_order", "PartialOrder"),
        ("exact", "Exact"),
    ):
        ranking = comparison.get("rankings", {}).get(metric)
        if not ranking or set(ranking) != expected:
            raise ValueError(f"missing or invalid {metric} ranking")
        best = ranking[0]
        lines.append(f"\\newcommand{{\\VTwoBest{macro}Model}}{{{display_labels[best]}}}")
        lines.append(
            f"\\newcommand{{\\VTwoBest{macro}Score}}{{{pct(comparison['aggregate'][best][metric])}\\%}}"
        )

    qwen_ids = [model_id for model_id, _, _ in MODEL_SPECS if model_id.startswith("Qwen/Qwen3-")]
    qwen_goal = [comparison["aggregate"][model_id]["goal_valid"] for model_id in qwen_ids]
    lines.append(
        r"\newcommand{\VTwoQwenGoalMonotonic}{%s}"
        % ("yes" if qwen_goal[0] < qwen_goal[1] < qwen_goal[2] else "no")
    )
    for metric, macro in (
        ("exact", "Exact"),
        ("partial_order", "PartialOrder"),
        ("goal_valid", "Goal"),
    ):
        count = sum(
            pair["metric_differences"][metric]["holm_adjusted_p_value"] < 0.05
            for pair in pairs
        )
        lines.append(f"\\newcommand{{\\VTwoSignificant{macro}PairCount}}{{{count}}}")

    behavior_gaps = {
        model_id: comparison["aggregate"][model_id]["goal_valid"]
        - comparison["aggregate"][model_id]["exact"]
        for model_id in ordered_model_ids
    }
    largest_behavior_model = max(behavior_gaps, key=behavior_gaps.get)
    lines.extend(
        (
            r"\newcommand{\VTwoBehaviorGapModelCount}{%d}"
            % sum(value > 1e-12 for value in behavior_gaps.values()),
            r"\newcommand{\VTwoLargestBehaviorGapModel}{%s}"
            % display_labels[largest_behavior_model],
            r"\newcommand{\VTwoLargestBehaviorGap}{%s}"
            % pct(behavior_gaps[largest_behavior_model]),
            r"\newcommand{\VTwoOutsideFamilyModelCount}{%d}"
            % sum(
                comparison["aggregate"][model_id]["goal_valid"]
                - comparison["aggregate"][model_id]["partial_order"]
                > 1e-12
                for model_id in ordered_model_ids
            ),
        )
    )

    prefix_goal_deltas = {
        model_id: sensitivity_by_model[model_id]["normalized_goal_valid_rate"]
        - sensitivity_by_model[model_id]["strict_goal_valid_rate"]
        for model_id in ordered_model_ids
    }
    largest_prefix_model = max(prefix_goal_deltas, key=prefix_goal_deltas.get)
    lines.extend(
        (
            r"\newcommand{\VTwoPrefixChangedModelCount}{%d}"
            % sum(value > 1e-12 for value in prefix_goal_deltas.values()),
            r"\newcommand{\VTwoLargestPrefixGoalDeltaModel}{%s}"
            % display_labels[largest_prefix_model],
            r"\newcommand{\VTwoLargestPrefixGoalDelta}{%s}"
            % pct(prefix_goal_deltas[largest_prefix_model]),
        )
    )

    catalog_goal_deltas = {
        model_id: catalog_by_model[model_id]["projected_goal_valid_rate"]
        - catalog_by_model[model_id]["strict_goal_valid_rate"]
        for model_id in ordered_model_ids
    }
    largest_catalog_model = max(catalog_goal_deltas, key=catalog_goal_deltas.get)
    lines.extend(
        (
            r"\newcommand{\VTwoCatalogChangedModelCount}{%d}"
            % sum(value > 1e-12 for value in catalog_goal_deltas.values()),
            r"\newcommand{\VTwoLargestCatalogGoalDeltaModel}{%s}"
            % display_labels[largest_catalog_model],
            r"\newcommand{\VTwoLargestCatalogGoalDelta}{%s}"
            % pct(catalog_goal_deltas[largest_catalog_model]),
        )
    )

    sampling_goal_gains = {
        model_id: comparison["aggregate"][model_id]["any_of_five_goal_valid"]
        - comparison["aggregate"][model_id]["single_sample_goal_valid"]
        for model_id in ordered_model_ids
    }
    largest_sampling_model = max(sampling_goal_gains, key=sampling_goal_gains.get)
    lines.extend(
        (
            r"\newcommand{\VTwoLargestSamplingGainModel}{%s}"
            % display_labels[largest_sampling_model],
            r"\newcommand{\VTwoLargestSamplingGain}{%s}"
            % pct(sampling_goal_gains[largest_sampling_model]),
        )
    )

    model_rows = []
    sensitivity_rows = []
    catalog_rows = []
    qwen_rows = []
    diversity_rows = []
    model_ci_rows = []
    for model_id, label, _ in MODEL_SPECS:
        metrics = comparison["aggregate"][model_id]
        model_rows.append(
            f"{label} & {pct(metrics['parse'])} & {pct(metrics['executable'])} & "
            f"{pct(metrics['goal_valid'])} & {pct(metrics['partial_order'])} & "
            f"{pct(metrics['exact'])} & {pct(metrics['false_rejection_among_valid'])} \\\\"
        )
        item = sensitivity_by_model[model_id]
        sensitivity_rows.append(
            f"{label} & {pct(item['strict_parse_rate'])} & {pct(item['normalized_parse_rate'])} & "
            f"{pct(item['strict_goal_valid_rate'])} & {pct(item['normalized_goal_valid_rate'])} & "
            f"{pct(item['strict_exact_match_rate'])} & {pct(item['normalized_exact_match_rate'])} \\\\"
        )
        catalog = catalog_by_model[model_id]
        catalog_rows.append(
            f"{label} & {pct(catalog['strict_parse_rate'])} & {pct(catalog['projected_parse_rate'])} & "
            f"{pct(catalog['strict_goal_valid_rate'])} & {pct(catalog['projected_goal_valid_rate'])} & "
            f"{pct(catalog['strict_exact_match_rate'])} & {pct(catalog['projected_exact_match_rate'])} \\\\"
        )
        diversity_rows.append(
            f"{label} & {pct(metrics['single_sample_goal_valid'])} & "
            f"{pct(metrics['any_of_five_goal_valid'])} & "
            f"{pct(metrics['mean_reference_family_coverage'])} & "
            f"{100 * metrics['mean_normalized_cost_regret_among_valid']:.1f} \\\\"
        )
        bootstrap = analyses[model_id].get("bootstrap", {}).get("metrics", {})
        metric_map = (
            ("goal_valid_rate", "goal_valid"),
            ("partial_order_match_rate", "partial_order"),
            ("exact_match_rate", "exact"),
            ("single_reference_false_rejection_among_valid", "false_rejection_among_valid"),
        )
        if any(key not in bootstrap for key, _ in metric_map):
            raise ValueError(f"missing bootstrap metrics for {model_id}")
        for key, aggregate_key in metric_map:
            if abs(bootstrap[key]["estimate"] - metrics[aggregate_key]) > 1e-12:
                raise ValueError(f"aggregate/bootstrap mismatch for {model_id} {key}")
        model_ci_rows.append(
            f"{label} & {rate_ci(bootstrap['goal_valid_rate'])} & "
            f"{rate_ci(bootstrap['partial_order_match_rate'])} & "
            f"{rate_ci(bootstrap['exact_match_rate'])} & "
            f"{rate_ci(bootstrap['single_reference_false_rejection_among_valid'])} \\\\"
        )
        if model_id.startswith("Qwen/Qwen3-"):
            qwen_rows.append(
                f"{label} & {pct(metrics['goal_valid'])} & {pct(metrics['partial_order'])} & "
                f"{pct(metrics['exact'])} \\\\"
            )
    for name, rows in (
        ("VTwoModelRows", model_rows),
        ("VTwoSensitivityRows", sensitivity_rows),
        ("VTwoCatalogProjectionRows", catalog_rows),
        ("VTwoQwenScaleRows", qwen_rows),
        ("VTwoDiversityRows", diversity_rows),
        ("VTwoModelCIRows", model_ci_rows),
    ):
        lines.append(f"\\newcommand{{\\{name}}}{{%")
        lines.extend(row + "%" for row in rows)
        lines.append("}")

    pair_rows = []
    pair_by_models = {
        frozenset((pair["left_model"], pair["right_model"])): pair for pair in pairs
    }
    for pair in pairs:
        pair_rows.append(
            pair_row(pair["left_model"], pair["right_model"], pair["metric_differences"])
        )
    lines.append("\\newcommand{\\VTwoAllPairRows}{%")
    lines.extend(row + "%" for row in pair_rows)
    lines.append("}")

    selected_rows = []
    for left, right in SELECTED_PAIRS:
        pair = pair_by_models.get(frozenset((left, right)))
        if pair is None:
            raise ValueError(f"missing pre-specified selected pair: {left}, {right}")
        selected_rows.append(pair_row(left, right, orient_pair(pair, left, right)))
    lines.append("\\newcommand{\\VTwoSelectedPairRows}{%")
    lines.extend(row + "%" for row in selected_rows)
    lines.append("}")

    split_names = (
        ("iid_core", "Core"),
        ("ood_commutation", "Commutation"),
        ("ood_goal_choice", "Goal choice"),
        ("ood_long_horizon", "Long horizon"),
        ("ood_operator_composition", "Operator composition"),
    )
    split_rows = []
    first_id = MODEL_SPECS[0][0]
    for split, label in split_names:
        count = analyses[first_id]["strata"]["structural_split"][split]["task_count"]
        values = [
            pct(analyses[model_id]["strata"]["structural_split"][split]["goal_valid_rate"])
            for model_id, _, _ in MODEL_SPECS
        ]
        split_rows.append(f"{label} & {count} & " + " & ".join(values) + r" \\")
    lines.append("\\newcommand{\\VTwoStructuralSplitRows}{%")
    lines.extend(row + "%" for row in split_rows)
    lines.append("}")

    # Native PGFPlots figures consume generated coordinates so that the
    # manuscript cannot silently retain values from an older matrix.
    figure_order = (
        "allenai/OLMo-2-1124-7B-Instruct",
        "microsoft/Phi-4-mini-instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "Qwen/Qwen3-8B",
        "Qwen/Qwen3-4B",
        "Qwen/Qwen3-14B",
    )

    def coordinates(metric: str) -> str:
        return " ".join(
            f"({pct(comparison['aggregate'][model_id][metric])},{index})"
            for index, model_id in enumerate(figure_order, start=1)
        )

    lines.extend(
        (
            r"\newcommand{\VTwoFigureExactCoordinates}{%s}" % coordinates("exact"),
            r"\newcommand{\VTwoFigurePartialCoordinates}{%s}"
            % coordinates("partial_order"),
            r"\newcommand{\VTwoFigureGoalCoordinates}{%s}"
            % coordinates("goal_valid"),
        )
    )
    lines.append(r"\newcommand{\VTwoFigureGapSegments}{%")
    for index, model_id in enumerate(figure_order, start=1):
        metrics = comparison["aggregate"][model_id]
        lines.append(
            r"\addplot[psGrid,line width=2.2pt] coordinates {(%s,%d) (%s,%d)};%%"
            % (pct(metrics["exact"]), index, pct(metrics["goal_valid"]), index)
        )
    lines.append("}")
    lines.append(r"\newcommand{\VTwoFigureGapAnnotations}{%")
    for index, model_id in enumerate(figure_order, start=1):
        metrics = comparison["aggregate"][model_id]
        gap = 100 * (metrics["goal_valid"] - metrics["exact"])
        if gap > 3:
            midpoint = 50 * (metrics["goal_valid"] + metrics["exact"])
            lines.append(
                r"\node[font=\sffamily\scriptsize,text=psAccent,anchor=south] at (axis cs:%.1f,%.2f) {+%.1f};%%"
                % (midpoint, index + 0.12, gap)
            )
    lines.append("}")

    category_metrics = {
        "Exact": lambda item: item["exact"],
        "Nonref": lambda item: item["goal_valid"] - item["exact"],
        "Miss": lambda item: item["executable"] - item["goal_valid"],
        "Failed": lambda item: item["parse"] - item["executable"],
        "Parse": lambda item: 1.0 - item["parse"],
    }
    for name, getter in category_metrics.items():
        values = " ".join(
            f"({pct(getter(comparison['aggregate'][model_id]))},{display_labels[model_id]})"
            for model_id in figure_order
        )
        lines.append(f"\\newcommand{{\\VTwoFigureStage{name}Coordinates}}{{{values}}}")

    prefix = sensitivity_by_model[largest_prefix_model]
    prefix_values = {
        "StrictParse": prefix["strict_parse_rate"],
        "NormalizedParse": prefix["normalized_parse_rate"],
        "StrictGoal": prefix["strict_goal_valid_rate"],
        "NormalizedGoal": prefix["normalized_goal_valid_rate"],
        "StrictExact": prefix["strict_exact_match_rate"],
        "NormalizedExact": prefix["normalized_exact_match_rate"],
    }
    for name, value in prefix_values.items():
        lines.append(f"\\newcommand{{\\VTwoPrefix{name}}}{{{pct(value)}\\%}}")
    for short, strict_key, normalized_key in (
        ("Parse", "strict_parse_rate", "normalized_parse_rate"),
        ("Goal", "strict_goal_valid_rate", "normalized_goal_valid_rate"),
        ("Exact", "strict_exact_match_rate", "normalized_exact_match_rate"),
    ):
        delta = 100 * (prefix[normalized_key] - prefix[strict_key])
        lines.append(f"\\newcommand{{\\VTwoPrefix{short}Delta}}{{{delta:.1f}}}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate table macros from a complete six-model matrix."
    )
    parser.add_argument("--artifact-suffix", default="v0_2")
    parser.add_argument("--task-count", type=int, default=100)
    parser.add_argument("--output-count", type=int, default=3000)
    parser.add_argument("--output", type=Path, default=PAPER / "generated_v02.tex")
    parser.add_argument("--coverage", type=Path, default=ARTIFACTS / "bounded_family_coverage_v0_1.json")
    args = parser.parse_args()
    suffix = args.artifact_suffix
    comparison = json.loads((ARTIFACTS / f"multi_model_comparison_{suffix}.json").read_text(encoding="utf-8"))
    sensitivity = json.loads((ARTIFACTS / f"action_prefix_sensitivity_comparison_{suffix}.json").read_text(encoding="utf-8"))
    catalog_projection = json.loads(
        (ARTIFACTS / f"catalog_projection_sensitivity_comparison_{suffix}_posthoc.json").read_text(
            encoding="utf-8"
        )
    )
    analyses = {}
    for model_id, _, slug in MODEL_SPECS:
        report = json.loads(
            (ARTIFACTS / f"{slug}_queue_{args.task_count}_analysis_{suffix}.json").read_text(
                encoding="utf-8"
            )
        )
        if report["model_id"] != model_id:
            raise ValueError(f"model mismatch for {slug}")
        analyses[model_id] = report
    selection = json.loads((ARTIFACTS / "selection_coverage_audit_v0_1.json").read_text(encoding="utf-8"))
    coverage = json.loads(args.coverage.read_text(encoding="utf-8"))
    output = args.output
    output.write_text(
        render(
            comparison,
            sensitivity,
            catalog_projection,
            analyses,
            selection,
            coverage,
            task_count=args.task_count,
            output_count=args.output_count,
        ).replace(
            "Generated by paper/scripts/generate_v02_data.py; do not edit.",
            f"Generated by paper/scripts/generate_v02_data.py from {suffix}; do not edit.",
        ),
        encoding="utf-8",
    )
    print(output)


if __name__ == "__main__":
    main()
