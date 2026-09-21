import importlib.util
from pathlib import Path

from planspace.core import GroundAction, PlanningProblem, fact


ROOT = Path(__file__).parents[1]


def load_script(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_independent_search_finds_nonreference_commutation_without_reference_input():
    module = load_script("audit_independent_state_search.py")
    left = GroundAction(
        "left", "MOVE", (), frozenset(), frozenset({fact("done", "left")}), frozenset()
    )
    right = GroundAction(
        "right", "MOVE", (), frozenset(), frozenset({fact("done", "right")}), frozenset()
    )
    problem = PlanningProblem(
        "commute", frozenset(), frozenset({fact("done", "left"), fact("done", "right")}), (left, right)
    )
    result = module.independent_search(
        problem,
        max_depth=2,
        max_solutions=8,
        max_expanded=100,
        paths_per_state=8,
        cost_slack=0,
    )
    assert sorted(result["solutions"]) == [["left", "right"], ["right", "left"]]


def test_exact_topological_count_is_independent_of_validation_cap():
    module = load_script("analyze_partial_order_cap_sensitivity.py")
    assert module.exact_topological_order_count(3, frozenset()) == 6
    assert module.exact_topological_order_count(3, frozenset({(0, 1), (1, 2)})) == 1


def test_incremental_cap_validation_matches_independent_orders():
    module = load_script("analyze_partial_order_cap_sensitivity.py")
    left = GroundAction(
        "left", "MOVE", (), frozenset(), frozenset({fact("done", "left")}), frozenset()
    )
    right = GroundAction(
        "right", "MOVE", (), frozenset(), frozenset({fact("done", "right")}), frozenset()
    )
    problem = PlanningProblem(
        "commute", frozenset(), frozenset({fact("done", "left"), fact("done", "right")}), (left, right)
    )
    rows = module.validate_topological_caps(problem, (left, right), frozenset(), [1, 2, 5])
    assert rows == [
        {"cap": 1, "checked": 1, "valid": 1, "all_valid": True},
        {"cap": 2, "checked": 2, "valid": 2, "all_valid": True},
        {"cap": 5, "checked": 2, "valid": 2, "all_valid": True},
    ]


def test_cost_bootstrap_interval_is_deterministic_and_bounded():
    module = load_script("analyze_cost_bounded_goal_validity.py")
    first = module.bootstrap_interval([0.0, 0.5, 1.0], trials=100, seed=7)
    second = module.bootstrap_interval([0.0, 0.5, 1.0], trials=100, seed=7)
    assert first == second
    assert 0 <= first[0] <= first[1] <= 1
