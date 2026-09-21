"""Run one real BDDL definition through the development-only action domain."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.core import action_ids, enumerate_valid_plans
from planspace.dev_domains import opening_packages_problem
from planspace.metrics import false_rejection_rate
from planspace.partial_order import dependency_edges, validate_topological_orders


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("problem", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = parse_problem_file(args.problem)
    problem = opening_packages_problem(source)
    enumeration = enumerate_valid_plans(problem, max_depth=len(problem.actions))
    if not enumeration.plans:
        raise RuntimeError("development pilot found no valid plan")
    reference = enumeration.plans[0]
    edges = dependency_edges(reference)
    valid_sorts, total_sorts = validate_topological_orders(problem, reference, edges)
    report = {
        "evidence_status": "real_bddl_development_semantics_not_paper_evidence",
        "problem_id": problem.problem_id,
        "source_sha256": hashlib.sha256(args.problem.read_bytes()).hexdigest(),
        "action_domain_version": "dev_opening_packages_v0.1",
        "plans": [action_ids(plan) for plan in enumeration.plans],
        "plan_count": len(enumeration.plans),
        "completeness_status": enumeration.completeness_status,
        "single_reference_false_rejection_rate": false_rejection_rate(
            problem, enumeration.plans, reference
        ),
        "partial_order_edges": sorted(edges),
        "valid_topological_sorts": valid_sorts,
        "total_topological_sorts": total_sorts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

