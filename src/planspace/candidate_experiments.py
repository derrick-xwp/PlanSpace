"""Deterministic sanity controls for candidate PlanSpace domains."""

from __future__ import annotations

import random
from collections.abc import Sequence

from .core import GroundAction, PlanningProblem, action_ids, execute_plan


def random_action_plan(
    problem: PlanningProblem, *, max_depth: int, rng: random.Random
) -> tuple[GroundAction, ...]:
    length = rng.randint(1, max_depth)
    actions = tuple(sorted(problem.actions, key=lambda item: item.action_id))
    return tuple(rng.choice(actions) for _ in range(length))


def random_enabled_plan(
    problem: PlanningProblem, *, max_depth: int, rng: random.Random
) -> tuple[GroundAction, ...]:
    state = problem.initial_state
    plan = []
    for _ in range(max_depth):
        enabled = sorted(
            (action for action in problem.actions if action.enabled(state)),
            key=lambda item: item.action_id,
        )
        if not enabled:
            break
        action = rng.choice(enabled)
        plan.append(action)
        state = action.apply(state)
        if problem.goal_satisfied(state):
            break
    return tuple(plan)


def evaluate_predictions(
    problem: PlanningProblem,
    predictions: Sequence[Sequence[GroundAction]],
    reference: Sequence[GroundAction],
) -> dict[str, float | int]:
    if not predictions:
        raise ValueError("at least one prediction is required")
    results = [execute_plan(problem, plan) for plan in predictions]
    reference_ids = action_ids(reference)
    attempts = len(predictions)
    return {
        "attempts": attempts,
        "exact_match_rate": sum(action_ids(plan) == reference_ids for plan in predictions)
        / attempts,
        "executable_rate": sum(result.executable for result in results) / attempts,
        "goal_success_rate": sum(result.valid for result in results) / attempts,
        "unique_plan_count": len({action_ids(plan) for plan in predictions}),
    }
