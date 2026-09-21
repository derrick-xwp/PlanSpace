"""Run the synthetic PlanSpace end-to-end smoke check."""

from __future__ import annotations

import json
from pathlib import Path

from examples.store_items import build_problem
from planspace.core import action_ids, enumerate_valid_plans, execute_plan
from planspace.metrics import false_rejection_rate
from planspace.partial_order import dependency_edges, validate_topological_orders


def main() -> None:
    problem, reference, alternative = build_problem()
    enumeration = enumerate_valid_plans(problem, max_depth=4)
    edges = dependency_edges(reference)
    valid_sorts, total_sorts = validate_topological_orders(problem, reference, edges)
    report = {
        "evidence_status": "synthetic_smoke_test_not_paper_evidence",
        "problem_id": problem.problem_id,
        "enumerated_plans": [action_ids(plan) for plan in enumeration.plans],
        "completeness_status": enumeration.completeness_status,
        "bound": {
            "type": enumeration.bound_type,
            "value": enumeration.bound_value,
            "cost_bound": enumeration.cost_bound,
        },
        "termination_reason": enumeration.termination_reason,
        "expanded_nodes": enumeration.expanded_nodes,
        "reference_valid": execute_plan(problem, reference).valid,
        "alternative_valid": execute_plan(problem, alternative).valid,
        "single_reference_false_rejection_rate": false_rejection_rate(
            problem, (reference, alternative), reference
        ),
        "partial_order_edges": sorted(edges),
        "valid_topological_sorts": valid_sorts,
        "total_topological_sorts": total_sorts,
    }
    output = Path("artifacts/smoke_metrics.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
