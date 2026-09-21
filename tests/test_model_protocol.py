import json
from pathlib import Path

import pytest

from examples.store_items import build_problem
from planspace.bddl_parser import parse_problem_file
from planspace.model_protocol import (
    parse_model_plan,
    parse_model_plan_action_prefix_sensitivity,
    parse_model_plan_catalog_projection_sensitivity,
    prompt_sha256,
    render_action_catalog_entry,
    render_context_fit_model_prompt,
    render_model_prompt,
)
from planspace.core import PlanningProblem, fact
from planspace.pilot_domains import storing_food_problem


def test_prompt_is_deterministic_and_does_not_label_a_reference():
    problem, _, _ = build_problem()
    first = render_model_prompt(problem)
    second = render_model_prompt(problem)
    assert first == second
    assert prompt_sha256(first) == prompt_sha256(second)
    assert "reference" not in first.lower()
    assert "Allowed action catalog" in first


def test_context_fit_prompt_is_deterministic_and_compacts_catalog_details():
    problem, _, _ = build_problem()
    canonical = render_model_prompt(problem)
    compact = render_context_fit_model_prompt(problem)
    assert compact == render_context_fit_model_prompt(problem)
    assert len(compact) < len(canonical)
    for action in problem.actions:
        assert f"action_id={action.action_id}; operator={action.operator}" in compact
        assert render_action_catalog_entry(action) not in compact


def test_plan_parser_accepts_json_and_rejects_invented_actions():
    allowed = {"pick_apple", "pick_book"}
    assert parse_model_plan('{"plan": ["pick_apple"]}', allowed) == ("pick_apple",)
    with pytest.raises(ValueError, match="unknown action_id"):
        parse_model_plan(json.dumps({"plan": ["invented"]}), allowed)


def test_prefix_sensitivity_removes_only_literal_catalog_prefix():
    allowed = {"open::window_1"}
    text = json.dumps({"plan": ["action_id=open::window_1"]})
    assert parse_model_plan_action_prefix_sensitivity(text, allowed) == (
        "open::window_1",
    )
    with pytest.raises(ValueError, match="after prefix normalization"):
        parse_model_plan_action_prefix_sensitivity(
            json.dumps({"plan": ["action=open::window_1"]}), allowed
        )


def test_catalog_projection_accepts_only_exact_rendered_records():
    problem, _, _ = build_problem()
    action = problem.actions[0]
    record = render_action_catalog_entry(action)
    text = json.dumps({"plan": [record]})
    assert parse_model_plan_catalog_projection_sensitivity(
        text, problem.actions
    ) == (action.action_id,)

    altered = record.replace("operator=", "operator =", 1)
    with pytest.raises(ValueError, match="after catalog projection"):
        parse_model_plan_catalog_projection_sensitivity(
            json.dumps({"plan": [altered]}), problem.actions
        )

    two_records_in_one_item = record + "; " + record
    with pytest.raises(ValueError, match="after catalog projection"):
        parse_model_plan_catalog_projection_sensitivity(
            json.dumps({"plan": [two_records_in_one_item]}), problem.actions
        )


def test_large_cartesian_goal_is_rendered_losslessly_and_compactly():
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "behavior_v3_9_2"
        / "storing_food_problem0.bddl"
    )
    problem = storing_food_problem(parse_problem_file(fixture))
    prompt = render_model_prompt(problem)
    assert "Goal alternatives (256, exact compact Cartesian form)" in prompt
    assert prompt.count("Choice group") == 8
    assert len(prompt) < 10_000


def test_large_non_cartesian_goal_is_rendered_losslessly_by_enumeration():
    common = fact("inside", "shared", "box")
    alternatives = tuple(
        frozenset(
            {
                common,
                fact("inside", f"item_{index}", f"container_{index % 3}"),
            }
        )
        for index in range(33)
    )
    problem = PlanningProblem(
        problem_id="large_non_cartesian",
        initial_state=frozenset(),
        goal=alternatives[0],
        actions=(),
        goal_alternatives=alternatives,
    )

    prompt = render_context_fit_model_prompt(problem)

    assert "Goal alternatives (33, exact compact enumerated form)" in prompt
    assert "- Common: inside(shared, box)" in prompt
    for index in range(33):
        assert (
            f"- G{index + 1}: inside(item_{index}, container_{index % 3})"
            in prompt
        )


def test_large_incomplete_cartesian_goal_is_rendered_by_enumeration():
    common = fact("inside", "shared", "box")
    pairs = [(left, right) for left in range(12) for right in range(3)][:34]
    alternatives = tuple(
        frozenset(
            {
                common,
                fact("inside", "item_a", f"container_{left}"),
                fact("inside", "item_b", f"container_{right}"),
            }
        )
        for left, right in pairs
    )
    problem = PlanningProblem(
        problem_id="large_incomplete_cartesian",
        initial_state=frozenset(),
        goal=alternatives[0],
        actions=(),
        goal_alternatives=alternatives,
    )

    prompt = render_context_fit_model_prompt(problem)

    assert "Goal alternatives (34, exact compact enumerated form)" in prompt
    assert "exact compact Cartesian form" not in prompt
    assert prompt.count("- G") == 34
