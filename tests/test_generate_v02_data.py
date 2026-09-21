import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "paper" / "scripts" / "generate_v02_data.py"
SPEC = importlib.util.spec_from_file_location("generate_v02_data", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixtures():
    aggregate = {}
    sensitivity_models = []
    catalog_models = []
    analyses = {}
    split_names = (
        "iid_core",
        "ood_commutation",
        "ood_goal_choice",
        "ood_long_horizon",
        "ood_operator_composition",
    )
    for model_id, _, _ in MODULE.MODEL_SPECS:
        aggregate[model_id] = {
            "parse": 1.0,
            "executable": 0.9,
            "goal_valid": 0.8,
            "partial_order": 0.7,
            "exact": 0.6,
            "false_rejection_among_valid": 0.25,
            "single_sample_goal_valid": 0.7,
            "any_of_five_goal_valid": 0.85,
            "mean_reference_family_coverage": 0.65,
            "mean_normalized_cost_regret_among_valid": 0.1,
        }
        sensitivity_models.append(
            {
                "model_id": model_id,
                "strict_parse_rate": 1.0,
                "normalized_parse_rate": 1.0,
                "strict_goal_valid_rate": 0.8,
                "normalized_goal_valid_rate": 0.8,
                "strict_exact_match_rate": 0.6,
                "normalized_exact_match_rate": 0.6,
            }
        )
        catalog_models.append(
            {
                "model_id": model_id,
                "strict_parse_rate": 1.0,
                "projected_parse_rate": 1.0,
                "strict_goal_valid_rate": 0.8,
                "projected_goal_valid_rate": 0.8,
                "strict_exact_match_rate": 0.6,
                "projected_exact_match_rate": 0.6,
            }
        )
        analyses[model_id] = {
            "bootstrap": {
                "metrics": {
                    "goal_valid_rate": {"estimate": 0.8, "ci95_low": 0.7, "ci95_high": 0.9},
                    "partial_order_match_rate": {"estimate": 0.7, "ci95_low": 0.6, "ci95_high": 0.8},
                    "exact_match_rate": {"estimate": 0.6, "ci95_low": 0.5, "ci95_high": 0.7},
                    "single_reference_false_rejection_among_valid": {
                        "estimate": 0.25,
                        "ci95_low": 0.15,
                        "ci95_high": 0.35,
                    },
                }
            },
            "strata": {
                "structural_split": {
                    split: {"task_count": 20, "goal_valid_rate": 0.8}
                    for split in split_names
                }
            }
        }
    pairs = []
    ids = list(aggregate)
    for left_index, left in enumerate(ids):
        for right in ids[left_index + 1 :]:
            metric = {
                "estimate": 0.1,
                "ci95_low": 0.02,
                "ci95_high": 0.18,
                "holm_adjusted_p_value": 0.04,
            }
            pairs.append(
                {
                    "left_model": left,
                    "right_model": right,
                    "metric_differences": {
                        "goal_valid": metric,
                        "partial_order": metric,
                        "exact": metric,
                    },
                }
            )
    rankings = {
        metric: list(aggregate)
        for metric in ("goal_valid", "partial_order", "exact")
    }
    comparison = {
        "aggregate": aggregate,
        "paired_comparisons": pairs,
        "rankings": rankings,
    }
    sensitivity = {"models": sensitivity_models}
    catalog = {
        "evidence_status": "posthoc_exploratory_interface_sensitivity",
        "models": catalog_models,
    }
    selection = {"funnel": [{"count": n} for n in (1016, 202, 120, 109, 100)]}
    coverage = {"summary": {"exhaustively_analyzed_task_count": 74, "micro_bounded_family_coverage": 0.9856}}
    return comparison, sensitivity, catalog, analyses, selection, coverage


def test_render_requires_and_emits_complete_six_model_evidence():
    text = MODULE.render(*fixtures())
    assert r"\newcommand{\VTwoModelCount}{6}" in text
    assert "Qwen3-14B" in text
    assert "OLMo-2-7B" in text
    assert r"\newcommand{\VTwoAllPairRows}" in text
    assert r"\newcommand{\VTwoSelectedPairRows}" in text
    assert text.count("Q3-8B $-$ Q3-14B") == 2
    assert text.count("Mistral $-$ OLMo") == 2
    assert r"\newcommand{\VTwoDiversityRows}" in text
    assert r"\newcommand{\VTwoModelCIRows}" in text
    assert r"\newcommand{\VTwoCatalogProjectionRows}" in text
    assert r"\newcommand{\VTwoQwenGoalMonotonic}{no}" in text
    assert r"\newcommand{\VTwoSignificantGoalPairCount}{15}" in text
    assert r"\newcommand{\VTwoFigureExactCoordinates}" in text
    assert r"\newcommand{\VTwoFigureGapSegments}" in text
    assert r"\newcommand{\VTwoFigureStageParseCoordinates}" in text
    assert r"\newcommand{\VTwoPrefixStrictParse}" in text
    assert r"\newcommand{\VTwoPrefixGoalDelta}" in text


def test_render_accepts_expanded_output_count():
    text = MODULE.render(*fixtures(), task_count=173, output_count=5190)
    assert r"\newcommand{\VTwoTaskCount}{173}" in text
    assert r"\newcommand{\VTwoSamplesPerTask}{5}" in text
    assert r"\newcommand{\VTwoOutputsPerModel}{865}" in text
    assert r"\newcommand{\VTwoOutputCount}{5,190}" in text


def test_render_fails_on_incomplete_matrix():
    comparison, *rest = fixtures()
    comparison["aggregate"].pop("Qwen/Qwen3-14B")
    with pytest.raises(ValueError, match="six-model aggregate"):
        MODULE.render(comparison, *rest)


def test_render_fails_on_duplicated_pairwise_comparison():
    comparison, *rest = fixtures()
    comparison["paired_comparisons"][-1] = comparison["paired_comparisons"][0]
    with pytest.raises(ValueError, match="duplicated, missing, or unexpected"):
        MODULE.render(comparison, *rest)


def test_orient_pair_reverses_effect_and_interval_only():
    pair = {
        "left_model": "Qwen/Qwen3-8B",
        "right_model": "Qwen/Qwen3-4B",
        "metric_differences": {
            "goal_valid": {
                "estimate": 0.2,
                "ci95_low": 0.1,
                "ci95_high": 0.3,
                "holm_adjusted_p_value": 0.04,
            }
        },
    }
    result = MODULE.orient_pair(pair, "Qwen/Qwen3-4B", "Qwen/Qwen3-8B")
    assert result["goal_valid"]["estimate"] == -0.2
    assert result["goal_valid"]["ci95_low"] == -0.3
    assert result["goal_valid"]["ci95_high"] == -0.1
    assert result["goal_valid"]["holm_adjusted_p_value"] == 0.04
