import pytest

from scripts.analyze_prompt_serialization_effect import paired_effect, task_rate
from scripts.verify_prompt_serialization_effect import assert_effect_equal


def _task(values):
    return {
        "samples": [
            {
                "parse_error": None if value else "parse failure",
                "execution": {"executable": value, "valid": value},
                "partial_order_match": value,
                "exact_match": value,
            }
            for value in values
        ]
    }


def test_task_rate_uses_all_samples():
    assert task_rate(_task([True, False, True, False]), "goal_valid") == 0.5


def test_paired_effect_is_new_minus_old_at_task_level():
    old = {"a": _task([False, False]), "b": _task([True, False])}
    new = {"a": _task([True, True]), "b": _task([True, False])}

    effect = paired_effect(old, new, "exact", trials=2_000, seed=7)

    assert effect["old_rate"] == pytest.approx(0.25)
    assert effect["new_rate"] == pytest.approx(0.75)
    assert effect["estimate"] == pytest.approx(0.5)
    assert effect["ci95_low"] <= effect["estimate"] <= effect["ci95_high"]


def test_paired_effect_rejects_mismatched_task_sets():
    with pytest.raises(ValueError, match="different task paths"):
        paired_effect({"a": _task([True])}, {"b": _task([True])}, "exact", trials=10, seed=1)


def test_effect_verifier_tolerates_only_machine_precision_drift():
    assert_effect_equal(
        {"estimate": 0.3880000000000001, "holm_reject_0_05": False},
        {"estimate": 0.38799999999999996, "holm_reject_0_05": False},
    )
    with pytest.raises(AssertionError):
        assert_effect_equal(
            {"estimate": 0.3881, "holm_reject_0_05": False},
            {"estimate": 0.3880, "holm_reject_0_05": False},
        )
