import unittest
from pathlib import Path

from planspace.action_abstraction import audit_action_abstraction
from planspace.bddl_parser import parse_problem_file
from planspace.pilot_domains import (
    installing_a_printer_problem,
    moving_boxes_to_storage_problem,
    opening_doors_problem,
    storing_food_problem,
)


FIXTURES = Path(__file__).parent / "fixtures" / "behavior_v3_9_2"


class ActionAbstractionAuditTest(unittest.TestCase):
    def _audit(self, task, filename, adapter):
        problem = adapter(parse_problem_file(FIXTURES / filename))
        return audit_action_abstraction(task, problem)

    def test_canonical_adapter_is_structurally_compliant(self):
        audit = self._audit(
            "opening_doors", "opening_doors_problem0.bddl", opening_doors_problem
        )
        self.assertEqual(
            audit.status, "structurally_compliant_pending_semantic_review"
        )
        self.assertEqual(audit.canonical_operators, ("NAVIGATE", "OPEN"))

    def test_printer_adapter_uses_high_level_transfer(self):
        audit = self._audit(
            "installing_a_printer",
            "installing_a_printer_problem0.bddl",
            installing_a_printer_problem,
        )
        self.assertEqual(
            audit.status, "structurally_compliant_pending_semantic_review"
        )
        self.assertEqual(audit.operators, ("TOGGLE_ON", "TRANSFER"))

    def test_storage_adapters_use_canonical_transfer(self):
        boxes = self._audit(
            "moving_boxes_to_storage",
            "moving_boxes_to_storage_problem0.bddl",
            moving_boxes_to_storage_problem,
        )
        food = self._audit(
            "storing_food", "storing_food_problem0.bddl", storing_food_problem
        )
        self.assertEqual(
            boxes.status, "structurally_compliant_pending_semantic_review"
        )
        self.assertEqual(
            food.status, "structurally_compliant_pending_semantic_review"
        )
        self.assertEqual(boxes.canonical_operators, ("TRANSFER",))
        self.assertEqual(food.canonical_operators, ("TRANSFER",))


if __name__ == "__main__":
    unittest.main()
