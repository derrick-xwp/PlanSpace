import unittest

from scripts.analyze_model_queue import sample_counts
from scripts.analyze_action_prefix_sensitivity import aggregate as aggregate_prefix_sensitivity
from scripts.analyze_sampling_curve import aggregate_prefix, task_prefix_metrics
from scripts.compare_model_matrix import holm_adjust, paired_bootstrap, paired_sign_flip_test


def sample(*, valid=False, executable=True, exact=False, partial=False, parse=True):
    return {
        "parse_error": None if parse else "bad output",
        "execution": (
            {"executable": executable, "valid": valid}
            if parse
            else None
        ),
        "exact_match": exact,
        "partial_order_match": partial,
    }


class ModelAnalysisTest(unittest.TestCase):
    def test_single_and_any_of_k_diversity_metrics(self):
        tasks = [
            {
                "samples": [
                    sample(valid=False, exact=False),
                    sample(valid=True, exact=False, partial=True),
                ],
                "metrics": {"unique_valid_prediction_count": 1},
            },
            {
                "samples": [
                    sample(valid=True, exact=True, partial=True),
                    sample(valid=True, exact=True, partial=True),
                ],
                "metrics": {"unique_valid_prediction_count": 1},
            },
        ]
        metrics = sample_counts(tasks)
        self.assertEqual(metrics["single_sample_goal_valid_rate"], 0.5)
        self.assertEqual(metrics["any_of_k_goal_valid_rate"], 1.0)
        self.assertEqual(metrics["any_of_k_exact_match_rate"], 0.5)
        self.assertEqual(metrics["goal_valid_rate"], 0.75)
        self.assertEqual(metrics["exact_match_rate"], 0.5)
        self.assertEqual(metrics["partial_order_match_rate"], 0.75)
        self.assertAlmostEqual(metrics["valid_prediction_uniqueness"], 2 / 3)

    def test_paired_bootstrap_uses_task_aligned_differences(self):
        left = {
            "a": {"samples": [sample(valid=True), sample(valid=True)]},
            "b": {"samples": [sample(valid=False), sample(valid=True)]},
        }
        right = {
            "a": {"samples": [sample(valid=False), sample(valid=True)]},
            "b": {"samples": [sample(valid=False), sample(valid=False)]},
        }
        result = paired_bootstrap(
            left, right, "goal_valid", trials=100, seed=7
        )
        self.assertEqual(result["estimate"], 0.5)
        self.assertLessEqual(result["ci95_low"], result["estimate"])
        self.assertGreaterEqual(result["ci95_high"], result["estimate"])

    def test_paired_sign_flip_and_holm_adjustment(self):
        left = {
            str(index): {"samples": [sample(valid=True)]}
            for index in range(8)
        }
        right = {
            str(index): {"samples": [sample(valid=False)]}
            for index in range(8)
        }
        p_value = paired_sign_flip_test(
            left, right, "goal_valid", trials=2000, seed=9
        )
        self.assertLess(p_value, 0.02)
        adjusted = holm_adjust([0.01, 0.04, 0.03])
        self.assertEqual(adjusted, [0.03, 0.06, 0.06])

    def test_sampling_prefix_separates_success_coverage_and_uniqueness(self):
        task = {
            "samples": [
                {
                    **sample(valid=True, partial=True),
                    "sample_index": 0,
                    "parsed_plan": ["a"],
                    "matched_reference_family_indices": [0],
                },
                {
                    **sample(valid=True, partial=True),
                    "sample_index": 1,
                    "parsed_plan": ["b"],
                    "matched_reference_family_indices": [1],
                },
            ],
            "reference_plan_dags": [{}, {}],
        }
        first = task_prefix_metrics(task, 1)
        second = aggregate_prefix([task], 2)
        self.assertEqual(first["any_goal_valid_rate"], 1.0)
        self.assertEqual(first["mean_reference_family_coverage"], 0.5)
        self.assertEqual(first["mean_unique_valid_plans"], 1.0)
        self.assertEqual(second["mean_reference_family_coverage"], 1.0)
        self.assertEqual(second["mean_unique_valid_plans"], 2.0)

    def test_prefix_sensitivity_aggregate_preserves_full_denominator(self):
        tasks = [
            {
                "samples": [
                    {
                        "strict_parse_success": False,
                        "normalized_parse_success": True,
                        "strict_goal_valid": False,
                        "normalized_goal_valid": True,
                        "strict_exact_match": False,
                        "normalized_exact_match": True,
                    },
                    {
                        "strict_parse_success": True,
                        "normalized_parse_success": True,
                        "strict_goal_valid": False,
                        "normalized_goal_valid": False,
                        "strict_exact_match": False,
                        "normalized_exact_match": False,
                    },
                ]
            }
        ]
        metrics = aggregate_prefix_sensitivity(tasks)
        self.assertEqual(metrics["sample_count"], 2)
        self.assertEqual(metrics["parse_rate_delta"], 0.5)
        self.assertEqual(metrics["goal_valid_rate_delta"], 0.5)
        self.assertEqual(metrics["exact_match_rate_delta"], 0.5)
        self.assertEqual(metrics["newly_recovered_valid_count"], 1)


if __name__ == "__main__":
    unittest.main()
