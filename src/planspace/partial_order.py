"""Conservative partial-order construction for grounded plans."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from functools import lru_cache

from .core import GroundAction, PlanningProblem, execute_plan


Edge = tuple[int, int]


def structurally_independent(left: GroundAction, right: GroundAction) -> bool:
    """Return whether two grounded actions have no conservative dependency.

    Positive effects that establish another action's precondition are treated
    as dependencies here. A later state-aware minimization pass may remove such
    an edge only after validating every newly admitted topological order.
    """

    if (left.add_effects | left.delete_effects) & right.preconditions:
        return False
    if (right.add_effects | right.delete_effects) & left.preconditions:
        return False
    if left.delete_effects & right.add_effects:
        return False
    if right.delete_effects & left.add_effects:
        return False

    spatial_names = {"inside", "ontop", "inroom", "onfloor", "draped"}

    def moved_subjects(action: GroundAction) -> set[str]:
        return {
            predicate.args[0]
            for predicate in action.add_effects | action.delete_effects
            if predicate.name in spatial_names and len(predicate.args) == 2
        }

    def access_symbols(action: GroundAction) -> set[str]:
        symbols = set(action.access_sources) | set(action.access_targets)
        for predicate in action.preconditions:
            if predicate.name in spatial_names:
                symbols.update(predicate.args)
        return symbols

    # Dynamic access guards read the current containment/support ancestry. If
    # one action moves a symbol named in the other's access chain, swapping the
    # two can change whether a closed ancestor is encountered.
    if moved_subjects(left) & access_symbols(right):
        return False
    if moved_subjects(right) & access_symbols(left):
        return False

    def polarity_subjects(action: GroundAction) -> set[str]:
        return {
            predicate.args[0]
            for predicate in action.add_effects | action.delete_effects
            if predicate.name in {"open", "not_open"} and len(predicate.args) == 1
        }

    if (
        "open_access_chains" in right.constraints
        and polarity_subjects(left) & right.gated_containers
    ):
        return False
    if (
        "open_access_chains" in left.constraints
        and polarity_subjects(right) & left.gated_containers
    ):
        return False
    return True


def operationally_independent(
    state: frozenset, left: GroundAction, right: GroundAction
) -> bool:
    """Check that both adjacent orders execute and reach the same state."""

    if not left.enabled(state) or not right.enabled(state):
        return False
    left_state = left.apply(state)
    right_state = right.apply(state)
    if not right.enabled(left_state) or not left.enabled(right_state):
        return False
    return right.apply(left_state) == left.apply(right_state)


def dependency_edges(plan: Sequence[GroundAction]) -> frozenset[Edge]:
    edges = {
        (left_index, right_index)
        for left_index, left in enumerate(plan)
        for right_index, right in enumerate(plan)
        if left_index < right_index and not structurally_independent(left, right)
    }
    return transitive_reduction(len(plan), edges)


def _reachable(node_count: int, edges: set[Edge], start: int, target: int) -> bool:
    adjacency = {node: [] for node in range(node_count)}
    for left, right in edges:
        adjacency[left].append(right)
    frontier = [start]
    visited = set()
    while frontier:
        node = frontier.pop()
        if node == target:
            return True
        if node in visited:
            continue
        visited.add(node)
        frontier.extend(adjacency[node])
    return False


def transitive_reduction(node_count: int, edges: set[Edge]) -> frozenset[Edge]:
    reduced = set(edges)
    for edge in sorted(edges):
        reduced.remove(edge)
        if not _reachable(node_count, reduced, edge[0], edge[1]):
            reduced.add(edge)
    return frozenset(reduced)


def topological_orders(
    node_count: int, edges: frozenset[Edge], *, limit: int | None = None
) -> Iterator[tuple[int, ...]]:
    predecessors = {node: set() for node in range(node_count)}
    successors = {node: set() for node in range(node_count)}
    for left, right in edges:
        predecessors[right].add(left)
        successors[left].add(right)

    yielded = 0

    def visit(prefix: tuple[int, ...], remaining: frozenset[int]) -> Iterator[tuple[int, ...]]:
        nonlocal yielded
        if limit is not None and yielded >= limit:
            return
        if not remaining:
            yielded += 1
            yield prefix
            return
        available = sorted(
            node for node in remaining if predecessors[node].isdisjoint(remaining)
        )
        for node in available:
            yield from visit(prefix + (node,), remaining - {node})

    yield from visit(tuple(), frozenset(range(node_count)))


def validate_topological_orders(
    problem: PlanningProblem,
    reference_plan: Sequence[GroundAction],
    edges: frozenset[Edge],
    *,
    limit: int | None = None,
) -> tuple[int, int]:
    total = 0
    valid = 0
    for order in topological_orders(len(reference_plan), edges, limit=limit):
        total += 1
        candidate = tuple(reference_plan[index] for index in order)
        valid += int(execute_plan(problem, candidate).valid)
    return valid, total


def matches_partial_order(
    candidate_action_ids: Sequence[str],
    reference_plan: Sequence[GroundAction],
    edges: frozenset[Edge],
) -> bool:
    """Return whether action IDs realize some topological order of a plan DAG.

    The memoized search handles repeated grounded action IDs without assuming
    that their occurrences can be paired greedily with reference nodes.
    """

    if len(candidate_action_ids) != len(reference_plan):
        return False
    node_count = len(reference_plan)
    predecessor_masks = [0] * node_count
    for left, right in edges:
        predecessor_masks[right] |= 1 << left
    reference_ids = tuple(action.action_id for action in reference_plan)

    @lru_cache(maxsize=None)
    def visit(position: int, remaining: int) -> bool:
        if position == len(candidate_action_ids):
            return remaining == 0
        wanted = candidate_action_ids[position]
        for node, action_id in enumerate(reference_ids):
            bit = 1 << node
            if not remaining & bit or action_id != wanted:
                continue
            if predecessor_masks[node] & remaining:
                continue
            if visit(position + 1, remaining ^ bit):
                return True
        return False

    return visit(0, (1 << node_count) - 1)
