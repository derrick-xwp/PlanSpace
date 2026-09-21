import unittest

from planspace.bddl_parser import parse_problem_text
from planspace.core import enumerate_valid_plans, execute_plan, fact
from planspace.dev_domains import opening_packages_problem
from planspace.partial_order import dependency_edges, validate_topological_orders
from planspace.translation import (
    UnsupportedGoalError,
    conjunctive_goal_facts,
    goal_alternatives,
    goal_quantifier_diagnostics,
)


OPENING_PACKAGES = """
(define (problem opening_packages_0)
  (:domain igibson)
  (:objects package_1 package_2 - package.n.02 floor_1 - floor.n.01)
  (:init
    (onfloor package_1 floor_1)
    (onfloor package_2 floor_1)
    (not (open package_1))
    (not (open package_2)))
  (:goal (and (forall (?package - package.n.02) (open ?package)))))
"""


class TranslationTest(unittest.TestCase):
    def test_forall_goal_is_grounded(self):
        source = parse_problem_text(OPENING_PACKAGES)
        self.assertEqual(
            conjunctive_goal_facts(source),
            frozenset({fact("open", "package_1"), fact("open", "package_2")}),
        )

    def test_dev_domain_recovers_both_orders(self):
        problem = opening_packages_problem(parse_problem_text(OPENING_PACKAGES))
        enumeration = enumerate_valid_plans(problem, max_depth=2)
        self.assertEqual(len(enumeration.plans), 2)
        for plan in enumeration.plans:
            self.assertTrue(execute_plan(problem, plan).valid)
        edges = dependency_edges(enumeration.plans[0])
        self.assertEqual(edges, frozenset())
        self.assertEqual(
            validate_topological_orders(problem, enumeration.plans[0], edges), (2, 2)
        )

    def test_existential_goal_is_rejected(self):
        source = parse_problem_text(
            OPENING_PACKAGES.replace(
                "(forall (?package - package.n.02) (open ?package))",
                "(exists (?package - package.n.02) (open ?package))",
            )
        )
        with self.assertRaises(UnsupportedGoalError):
            conjunctive_goal_facts(source)

    def test_existential_goal_becomes_witness_alternatives(self):
        source = parse_problem_text(
            OPENING_PACKAGES.replace(
                "(forall (?package - package.n.02) (open ?package))",
                "(exists (?package - package.n.02) (open ?package))",
            )
        )
        self.assertEqual(
            set(goal_alternatives(source)),
            {
                frozenset({fact("open", "package_1")}),
                frozenset({fact("open", "package_2")}),
            },
        )

    def test_disjunctive_goal_becomes_two_alternatives(self):
        source = parse_problem_text(
            OPENING_PACKAGES.replace(
                "(forall (?package - package.n.02) (open ?package))",
                "(or (open package_1) (open package_2))",
            )
        )
        self.assertEqual(len(goal_alternatives(source)), 2)

    def test_vacuous_quantifier_is_reported_without_silent_repair(self):
        source = parse_problem_text(
            OPENING_PACKAGES.replace(
                "(forall (?package - package.n.02) (open ?package))",
                "(forall (?package - package.n.02) (open package_1))",
            )
        )
        self.assertEqual(
            goal_quantifier_diagnostics(source),
            ({
                "kind": "vacuous_quantified_variable",
                "quantifier": "forall",
                "variable": "?package",
                "variable_type": "package.n.02",
            },),
        )


if __name__ == "__main__":
    unittest.main()
