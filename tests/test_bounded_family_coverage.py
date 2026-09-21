from examples.store_items import build_problem
from scripts.analyze_bounded_family_coverage import task_coverage


def test_bounded_family_coverage_is_exhaustive_on_small_problem():
    problem, reference, _ = build_problem()
    result = task_coverage(
        problem, max_depth=4, max_plans=1000, representatives=[reference]
    )
    assert result["search_exhaustive"] is True
    assert result["family_order_enumeration_exhaustive"] is True
    assert result["bounded_valid_plan_count"] > 0
    assert result["bounded_family_coverage"] == 1.0
