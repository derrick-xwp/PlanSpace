import unittest

from planspace.bddl_parser import parse_problem_text, predicate_names


SAMPLE = """
(define (problem storing_food_0)
  (:domain behavior-1k)
  (:objects
    apple_1 apple_2 - apple
    cabinet_1 - cabinet
    counter_1 - counter)
  (:init
    (ontop apple_1 counter_1)
    (ontop apple_2 counter_1)
    (closed cabinet_1))
  (:goal
    (and
      (inside ?apple_1 ?cabinet_1)
      (inside ?apple_2 ?cabinet_1)
      (closed ?cabinet_1))))
"""


class BDDLParserTest(unittest.TestCase):
    def test_preserves_problem_structure(self):
        problem = parse_problem_text(SAMPLE)
        self.assertEqual(problem.problem_name, "storing_food_0")
        self.assertEqual(problem.domain_name, "behavior-1k")
        self.assertEqual(len(problem.objects), 4)
        self.assertEqual(len(problem.initial), 3)
        self.assertEqual(predicate_names(problem.goal), frozenset({"inside", "closed"}))

    def test_rejects_unclosed_input(self):
        with self.assertRaises(ValueError):
            parse_problem_text(SAMPLE.rsplit(")", 1)[0])

    def test_quantifier_bindings_are_not_predicates(self):
        problem = parse_problem_text(
            SAMPLE.replace(
                "(inside ?apple_1 ?cabinet_1)",
                "(exists (?item - apple) (inside ?item ?cabinet_1))",
            )
        )
        self.assertEqual(predicate_names(problem.goal), frozenset({"inside", "closed"}))

    def test_multiple_goal_expressions_are_explicitly_conjoined(self):
        problem = parse_problem_text(
            SAMPLE.replace(
                "      (closed ?cabinet_1))))",
                "      (closed ?cabinet_1))\n    (not (open ?cabinet_1))))",
            )
        )
        self.assertTrue(problem.implicit_goal_conjunction)
        self.assertEqual(problem.goal[0], "and")
        self.assertEqual(predicate_names(problem.goal), frozenset({"inside", "closed", "open"}))


if __name__ == "__main__":
    unittest.main()
