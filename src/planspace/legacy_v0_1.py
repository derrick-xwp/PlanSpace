"""Minimal frozen executor and DAG builder for the archived v0.1 protocol.

The v0.5 uniform-compact artifacts were executed before the v0.4 constraint
checks and access-chain-aware DAG rules were introduced.  This module exists
solely to replay that recorded protocol; it is not an alternative evaluator
for new experiments.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from .core import Predicate, State


@dataclass(frozen=True)
class GroundAction:
    action_id: str
    operator: str
    args: tuple[str, ...]
    preconditions: frozenset[Predicate]
    add_effects: frozenset[Predicate]
    delete_effects: frozenset[Predicate]
    cost: float = 1.0

    def missing_preconditions(self, state: State) -> frozenset[Predicate]:
        return self.preconditions - state

    def enabled(self, state: State) -> bool:
        return not self.missing_preconditions(state)

    def apply(self, state: State) -> State:
        missing = self.missing_preconditions(state)
        if missing:
            rendered = ", ".join(sorted(map(str, missing)))
            raise ValueError(f"{self.action_id} missing preconditions: {rendered}")
        return frozenset((state - self.delete_effects) | self.add_effects)


@dataclass(frozen=True)
class PlanningProblem:
    problem_id: str
    initial_state: State
    goal: frozenset[Predicate]
    actions: tuple[GroundAction, ...]
    goal_alternatives: tuple[frozenset[Predicate], ...] = ()

    def goal_satisfied(self, state: State) -> bool:
        return any(alternative <= state for alternative in self.goal_alternatives or (self.goal,))


@dataclass(frozen=True)
class ExecutionResult:
    executable: bool
    goal_satisfied: bool
    final_state: State
    state_trace: tuple[State, ...]
    failure_step: int | None = None
    failed_action_id: str | None = None
    missing_preconditions: frozenset[Predicate] = frozenset()

    @property
    def valid(self) -> bool:
        return self.executable and self.goal_satisfied


def execute_plan(problem: PlanningProblem, plan: Sequence[GroundAction]) -> ExecutionResult:
    state = problem.initial_state
    trace = [state]
    for step, action in enumerate(plan):
        missing = action.missing_preconditions(state)
        if missing:
            return ExecutionResult(
                executable=False,
                goal_satisfied=False,
                final_state=state,
                state_trace=tuple(trace),
                failure_step=step,
                failed_action_id=action.action_id,
                missing_preconditions=missing,
            )
        state = action.apply(state)
        trace.append(state)
    return ExecutionResult(
        executable=True,
        goal_satisfied=problem.goal_satisfied(state),
        final_state=state,
        state_trace=tuple(trace),
    )


Edge = tuple[int, int]


def _independent(left: GroundAction, right: GroundAction) -> bool:
    return not (
        (left.add_effects | left.delete_effects) & right.preconditions
        or (right.add_effects | right.delete_effects) & left.preconditions
        or left.delete_effects & right.add_effects
        or right.delete_effects & left.add_effects
    )


def _reachable(node_count: int, edges: set[Edge], start: int, target: int) -> bool:
    adjacency = {node: [] for node in range(node_count)}
    for left, right in edges:
        adjacency[left].append(right)
    frontier = [start]
    seen: set[int] = set()
    while frontier:
        node = frontier.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        frontier.extend(adjacency[node])
    return False


def dependency_edges(plan: Sequence[GroundAction]) -> frozenset[Edge]:
    edges = {
        (left_index, right_index)
        for left_index, left in enumerate(plan)
        for right_index, right in enumerate(plan)
        if left_index < right_index and not _independent(left, right)
    }
    reduced = set(edges)
    for edge in sorted(edges):
        reduced.remove(edge)
        if not _reachable(len(plan), reduced, edge[0], edge[1]):
            reduced.add(edge)
    return frozenset(reduced)
