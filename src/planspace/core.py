"""Deterministic symbolic execution and bounded plan enumeration."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from typing import Iterable, Sequence


@dataclass(frozen=True, order=True)
class Predicate:
    name: str
    args: tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.name}({', '.join(self.args)})"


def fact(name: str, *args: str) -> Predicate:
    return Predicate(name=name, args=tuple(args))


State = frozenset[Predicate]


@dataclass(frozen=True)
class GroundAction:
    action_id: str
    operator: str
    args: tuple[str, ...]
    preconditions: frozenset[Predicate]
    add_effects: frozenset[Predicate]
    delete_effects: frozenset[Predicate]
    cost: float = 1.0
    constraints: tuple[str, ...] = ()
    access_sources: tuple[str, ...] = ()
    access_targets: tuple[str, ...] = ()
    gated_containers: frozenset[str] = frozenset()

    def missing_preconditions(self, state: State) -> frozenset[Predicate]:
        return self.preconditions - state

    def enabled(self, state: State) -> bool:
        return not self.missing_preconditions(state) and not self.constraint_violations(state)

    def required_open_containers(self, state: State) -> frozenset[str]:
        if "open_access_chains" not in self.constraints:
            return frozenset()
        parents: dict[str, set[str]] = {}
        for predicate in state:
            if (
                predicate.name in {"inside", "ontop", "draped"}
                and len(predicate.args) == 2
            ):
                parents.setdefault(predicate.args[0], set()).add(predicate.args[1])

        required = set()

        def visit(object_name: str, include_self: bool) -> None:
            frontier = [object_name] if include_self else list(parents.get(object_name, ()))
            seen = set()
            while frontier:
                current = frontier.pop()
                if current in seen:
                    continue
                seen.add(current)
                if (
                    current in self.gated_containers
                    and fact("open", current) not in state
                ):
                    required.add(current)
                frontier.extend(parents.get(current, ()))

        for item in self.access_sources:
            visit(item, False)
        for item in self.access_targets:
            visit(item, True)
        return frozenset(required)

    def constraint_violations(self, state: State) -> tuple[str, ...]:
        candidate = frozenset((state - self.delete_effects) | self.add_effects)
        violations = []
        if "spatial_irreflexive" in self.constraints and any(
            predicate.name in {"inside", "ontop"}
            and len(predicate.args) == 2
            and predicate.args[0] == predicate.args[1]
            for predicate in candidate
        ):
            violations.append("spatial_irreflexive")
        if "spatial_unique_location" in self.constraints:
            counts: dict[str, int] = {}
            for predicate in candidate:
                if (
                    predicate.name in {"inside", "ontop", "inroom", "onfloor", "draped"}
                    and len(predicate.args) == 2
                ):
                    counts[predicate.args[0]] = counts.get(predicate.args[0], 0) + 1
            if any(count > 1 for count in counts.values()):
                violations.append("spatial_unique_location")
        if "ontop_acyclic" in self.constraints:
            graph = {
                predicate.args[0]: predicate.args[1]
                for predicate in candidate
                if predicate.name == "ontop" and len(predicate.args) == 2
            }
            for start in graph:
                seen = set()
                node = start
                while node in graph:
                    if node in seen:
                        violations.append("ontop_acyclic")
                        break
                    seen.add(node)
                    node = graph[node]
                if "ontop_acyclic" in violations:
                    break
        if self.required_open_containers(state):
            violations.append("open_access_chains")
        return tuple(violations)

    def apply(self, state: State) -> State:
        missing = self.missing_preconditions(state)
        if missing:
            rendered = ", ".join(sorted(map(str, missing)))
            raise ValueError(f"{self.action_id} missing preconditions: {rendered}")
        violations = self.constraint_violations(state)
        if violations:
            raise ValueError(
                f"{self.action_id} violates constraints: {', '.join(violations)}"
            )
        return frozenset((state - self.delete_effects) | self.add_effects)


@dataclass(frozen=True)
class PlanningProblem:
    problem_id: str
    initial_state: State
    goal: frozenset[Predicate]
    actions: tuple[GroundAction, ...]
    goal_alternatives: tuple[frozenset[Predicate], ...] = ()

    def goal_satisfied(self, state: State) -> bool:
        alternatives = self.goal_alternatives or (self.goal,)
        return any(alternative <= state for alternative in alternatives)


@dataclass(frozen=True)
class ExecutionResult:
    executable: bool
    goal_satisfied: bool
    final_state: State
    state_trace: tuple[State, ...]
    failure_step: int | None = None
    failed_action_id: str | None = None
    missing_preconditions: frozenset[Predicate] = frozenset()
    constraint_violations: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return self.executable and self.goal_satisfied


def execute_plan(
    problem: PlanningProblem, plan: Sequence[GroundAction]
) -> ExecutionResult:
    state = problem.initial_state
    trace = [state]
    for step, action in enumerate(plan):
        missing = action.missing_preconditions(state)
        violations = action.constraint_violations(state)
        if missing or violations:
            return ExecutionResult(
                executable=False,
                goal_satisfied=False,
                final_state=state,
                state_trace=tuple(trace),
                failure_step=step,
                failed_action_id=action.action_id,
                missing_preconditions=missing,
                constraint_violations=violations,
            )
        state = action.apply(state)
        trace.append(state)
    return ExecutionResult(
        executable=True,
        goal_satisfied=problem.goal_satisfied(state),
        final_state=state,
        state_trace=tuple(trace),
    )


@dataclass(frozen=True)
class PlanEnumeration:
    plans: tuple[tuple[GroundAction, ...], ...]
    completeness_status: str
    bound_type: str
    bound_value: int
    cost_bound: float | None
    termination_reason: str
    expanded_nodes: int


def enumerate_valid_plans(
    problem: PlanningProblem,
    *,
    max_depth: int,
    max_cost: float | None = None,
    max_plans: int | None = None,
    deduplicate_states: bool = False,
) -> PlanEnumeration:
    """Enumerate simple-state-path valid plans within declared bounds.

    This implementation is deliberately conservative: paths that revisit an
    earlier symbolic state are omitted. The restriction prevents reversible
    loops from dominating the pilot search and is recorded in the returned
    completeness status.
    """

    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    cost_bound = float("inf") if max_cost is None else max_cost
    serial = count()
    queue: list[tuple[float, int, int, State, tuple[GroundAction, ...], frozenset[State]]] = []
    heappush(
        queue,
        (0.0, 0, next(serial), problem.initial_state, tuple(), frozenset({problem.initial_state})),
    )
    plans: list[tuple[GroundAction, ...]] = []
    expanded = 0
    capped = False
    seen_states = {problem.initial_state}

    while queue:
        cost, depth, _, state, plan, path_states = heappop(queue)
        if problem.goal_satisfied(state):
            plans.append(plan)
            if max_plans is not None and len(plans) >= max_plans:
                capped = bool(queue)
                break
            continue
        if depth >= max_depth:
            continue
        expanded += 1
        for action in sorted(problem.actions, key=lambda item: item.action_id):
            next_cost = cost + action.cost
            if next_cost > cost_bound or not action.enabled(state):
                continue
            next_state = action.apply(state)
            if next_state in path_states:
                continue
            if deduplicate_states and next_state in seen_states:
                continue
            if deduplicate_states:
                seen_states.add(next_state)
            heappush(
                queue,
                (
                    next_cost,
                    depth + 1,
                    next(serial),
                    next_state,
                    plan + (action,),
                    path_states | {next_state},
                ),
            )

    if capped:
        status = "sampled"
    elif deduplicate_states:
        status = "bounded_complete_unique_states"
    else:
        status = "bounded_complete_simple_paths"
    reason = "max_plans_reached" if capped else "bounded_search_exhausted"
    return PlanEnumeration(
        plans=tuple(plans),
        completeness_status=status,
        bound_type="plan_length",
        bound_value=max_depth,
        cost_bound=max_cost,
        termination_reason=reason,
        expanded_nodes=expanded,
    )


def action_ids(plan: Iterable[GroundAction]) -> tuple[str, ...]:
    return tuple(action.action_id for action in plan)
