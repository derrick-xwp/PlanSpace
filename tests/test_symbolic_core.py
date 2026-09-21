import unittest

from examples.store_items import build_problem
from planspace.core import enumerate_valid_plans, execute_plan
from planspace.metrics import false_rejection_rate
from planspace.partial_order import (
    dependency_edges,
    matches_partial_order,
    operationally_independent,
    validate_topological_orders,
)


class SymbolicCoreTest(unittest.TestCase):
    def setUp(self):
        self.problem, self.plan_a, self.plan_b = build_problem()

    def test_both_interleavings_are_valid(self):
        self.assertTrue(execute_plan(self.problem, self.plan_a).valid)
        self.assertTrue(execute_plan(self.problem, self.plan_b).valid)

    def test_premature_close_has_localized_failure(self):
        invalid = (self.plan_a[0], self.plan_a[3], self.plan_a[1], self.plan_a[2])
        result = execute_plan(self.problem, invalid)
        self.assertFalse(result.valid)
        self.assertEqual(result.failure_step, 3)
        self.assertEqual(result.failed_action_id, "place_apple")

    def test_open_and_grasp_commute(self):
        self.assertTrue(
            operationally_independent(
                self.problem.initial_state, self.plan_a[0], self.plan_a[1]
            )
        )

    def test_partial_order_admits_exactly_two_valid_orders(self):
        edges = dependency_edges(self.plan_a)
        valid, total = validate_topological_orders(self.problem, self.plan_a, edges)
        self.assertEqual((valid, total), (2, 2))

    def test_partial_order_match_accepts_reordering(self):
        edges = dependency_edges(self.plan_a)
        candidate = [self.plan_a[1].action_id, self.plan_a[0].action_id]
        self.assertFalse(matches_partial_order(candidate, self.plan_a, edges))
        candidate = [
            self.plan_a[1].action_id,
            self.plan_a[0].action_id,
            self.plan_a[2].action_id,
            self.plan_a[3].action_id,
        ]
        self.assertTrue(matches_partial_order(candidate, self.plan_a, edges))

    def test_partial_order_match_rejects_wrong_multiset(self):
        edges = dependency_edges(self.plan_a)
        candidate = [action.action_id for action in self.plan_a]
        candidate[-1] = candidate[0]
        self.assertFalse(matches_partial_order(candidate, self.plan_a, edges))

    def test_bounded_enumeration_recovers_two_plans(self):
        result = enumerate_valid_plans(self.problem, max_depth=4)
        ids = {tuple(action.action_id for action in plan) for plan in result.plans}
        self.assertEqual(
            ids,
            {
                ("open_cabinet", "grasp_apple", "place_apple", "close_cabinet"),
                ("grasp_apple", "open_cabinet", "place_apple", "close_cabinet"),
            },
        )

    def test_exact_match_false_rejects_one_valid_plan(self):
        rate = false_rejection_rate(
            self.problem, (self.plan_a, self.plan_b), self.plan_a
        )
        self.assertEqual(rate, 0.5)


if __name__ == "__main__":
    unittest.main()
