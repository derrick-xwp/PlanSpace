import random

from examples.store_items import build_problem
from planspace.candidate_experiments import (
    evaluate_predictions,
    random_action_plan,
    random_enabled_plan,
)


def test_random_controls_are_seeded_and_metric_separation_is_explicit():
    problem, valid, _ = build_problem()
    first = random_action_plan(problem, max_depth=4, rng=random.Random(7))
    second = random_action_plan(problem, max_depth=4, rng=random.Random(7))
    assert first == second

    metrics = evaluate_predictions(problem, [valid, tuple()], valid)
    assert metrics["attempts"] == 2
    assert metrics["exact_match_rate"] == 0.5
    assert metrics["executable_rate"] == 1.0
    assert metrics["goal_success_rate"] == 0.5


def test_random_enabled_control_never_emits_an_inapplicable_action():
    problem, _, _ = build_problem()
    for seed in range(20):
        plan = random_enabled_plan(problem, max_depth=4, rng=random.Random(seed))
        metrics = evaluate_predictions(problem, [plan], plan)
        assert metrics["executable_rate"] == 1.0
