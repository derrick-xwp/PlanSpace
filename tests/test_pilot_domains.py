import unittest
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import enumerate_valid_plans, execute_plan
from planspace.partial_order import dependency_edges, validate_topological_orders
from planspace.pilot_domains import (
    installing_a_printer_problem,
    moving_boxes_to_storage_problem,
    opening_doors_problem,
    organizing_file_cabinet_problem,
    storing_food_problem,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "behavior_v3_9_2"
    / "opening_doors_problem0.bddl"
)
PRINTER_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "behavior_v3_9_2"
    / "installing_a_printer_problem0.bddl"
)
CABINET_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "behavior_v3_9_2"
    / "organizing_file_cabinet_problem0.bddl"
)
BOXES_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "behavior_v3_9_2"
    / "moving_boxes_to_storage_problem0.bddl"
)
FOOD_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "behavior_v3_9_2"
    / "storing_food_problem0.bddl"
)


class PilotDomainsTest(unittest.TestCase):
    def test_opening_doors_recovers_both_visit_orders(self):
        problem = opening_doors_problem(parse_problem_file(FIXTURE))
        enumeration = enumerate_valid_plans(problem, max_depth=4)
        self.assertEqual(len(enumeration.plans), 2)
        self.assertEqual(sorted(map(len, enumeration.plans)), [3, 4])
        for plan in enumeration.plans:
            self.assertTrue(execute_plan(problem, plan).valid)
            edges = dependency_edges(plan)
            self.assertEqual(
                validate_topological_orders(problem, plan, edges), (1, 1)
            )

    def test_installing_printer_has_one_high_level_causal_plan(self):
        problem = installing_a_printer_problem(parse_problem_file(PRINTER_FIXTURE))
        enumeration = enumerate_valid_plans(problem, max_depth=2)
        self.assertEqual(len(enumeration.plans), 1)
        plan = enumeration.plans[0]
        self.assertEqual([action.operator for action in plan], ["TRANSFER", "TOGGLE_ON"])
        self.assertTrue(execute_plan(problem, plan).valid)
        edges = dependency_edges(plan)
        self.assertEqual(validate_topological_orders(problem, plan, edges), (1, 1))

    def test_installing_printer_rejects_premature_toggle(self):
        problem = installing_a_printer_problem(parse_problem_file(PRINTER_FIXTURE))
        toggle = next(action for action in problem.actions if action.operator == "TOGGLE_ON")
        result = execute_plan(problem, [toggle])
        self.assertFalse(result.executable)
        self.assertEqual(result.failed_action_id, "toggle_on::printer.n.03_1")

    def test_file_cabinet_filters_satisfied_objects_and_recovers_permutations(self):
        problem = organizing_file_cabinet_problem(parse_problem_file(CABINET_FIXTURE))
        self.assertEqual(len(problem.goal), 7)
        self.assertEqual(len(problem.actions), 5)
        action_ids = {action.action_id for action in problem.actions}
        self.assertFalse(any("document.n.01_2" in item for item in action_ids))
        self.assertFalse(any("document.n.01_4" in item for item in action_ids))

        enumeration = enumerate_valid_plans(problem, max_depth=5)
        self.assertEqual(len(enumeration.plans), 120)
        self.assertEqual({len(plan) for plan in enumeration.plans}, {5})
        first_plan = enumeration.plans[0]
        self.assertTrue(execute_plan(problem, first_plan).valid)
        edges = dependency_edges(first_plan)
        self.assertEqual(edges, frozenset())
        self.assertEqual(validate_topological_orders(problem, first_plan, edges), (120, 120))

    def test_moving_boxes_preserves_both_stacking_goals(self):
        problem = moving_boxes_to_storage_problem(parse_problem_file(BOXES_FIXTURE))
        self.assertEqual(len(problem.goal_alternatives), 2)
        self.assertEqual(len(problem.actions), 6)

        enumeration = enumerate_valid_plans(problem, max_depth=3)
        self.assertEqual(len(enumeration.plans), 6)
        self.assertEqual(sorted(map(len, enumeration.plans)), [2, 2, 3, 3, 3, 3])
        achieved_goals = set()
        for plan in enumeration.plans:
            execution = execute_plan(problem, plan)
            self.assertTrue(execution.valid)
            achieved_goals.update(
                index
                for index, goal in enumerate(problem.goal_alternatives)
                if goal <= execution.final_state
            )
        self.assertEqual(achieved_goals, {0, 1})

    def test_storing_food_covers_all_cabinet_assignments(self):
        problem = storing_food_problem(parse_problem_file(FOOD_FIXTURE))
        self.assertEqual(len(problem.goal_alternatives), 256)
        self.assertEqual(len(problem.actions), 16)

        enumeration = enumerate_valid_plans(
            problem, max_depth=8, deduplicate_states=True
        )
        self.assertEqual(enumeration.completeness_status, "bounded_complete_unique_states")
        self.assertEqual(len(enumeration.plans), 256)
        self.assertEqual({len(plan) for plan in enumeration.plans}, {8})
        final_states = {execute_plan(problem, plan).final_state for plan in enumeration.plans}
        self.assertEqual(len(final_states), 256)
        self.assertTrue(all(execute_plan(problem, plan).valid for plan in enumeration.plans))

        first_plan = enumeration.plans[0]
        edges = dependency_edges(first_plan)
        self.assertEqual(edges, frozenset())
        self.assertEqual(
            validate_topological_orders(problem, first_plan, edges, limit=1000),
            (1000, 1000),
        )


if __name__ == "__main__":
    unittest.main()
