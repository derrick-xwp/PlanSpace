"""Reference and execution-based plan metrics."""

from __future__ import annotations

from collections.abc import Sequence

from .core import GroundAction, PlanningProblem, action_ids, execute_plan


def exact_reference_match(
    candidate: Sequence[GroundAction], reference: Sequence[GroundAction]
) -> bool:
    return action_ids(candidate) == action_ids(reference)


def execution_validity(problem: PlanningProblem, candidate: Sequence[GroundAction]) -> bool:
    return execute_plan(problem, candidate).valid


def false_rejection_rate(
    problem: PlanningProblem,
    candidates: Sequence[Sequence[GroundAction]],
    reference: Sequence[GroundAction],
) -> float:
    valid_candidates = [plan for plan in candidates if execution_validity(problem, plan)]
    if not valid_candidates:
        raise ValueError("false rejection rate requires at least one valid candidate")
    rejected = sum(not exact_reference_match(plan, reference) for plan in valid_candidates)
    return rejected / len(valid_candidates)

