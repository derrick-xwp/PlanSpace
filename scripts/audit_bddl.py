"""Audit a BDDL activity-definition directory without assigning action semantics."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from planspace.bddl_parser import parse_problem_file, predicate_names


def _stable_counts(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("activity_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--source-label",
        help="Canonical source label used instead of a host-specific absolute path",
    )
    args = parser.parse_args()

    paths = sorted(args.activity_root.glob("*/problem*.bddl"))
    records = []
    initial_counts: Counter[str] = Counter()
    goal_counts: Counter[str] = Counter()
    failures = []
    for path in paths:
        try:
            problem = parse_problem_file(path)
            init_names = set()
            for expression in problem.initial:
                init_names.update(predicate_names(expression))
            goal_names = predicate_names(problem.goal)
            initial_counts.update(init_names)
            goal_counts.update(goal_names)
            records.append(
                {
                    "problem_name": problem.problem_name,
                    "source_path": path.relative_to(args.activity_root).as_posix(),
                    "object_count": len(problem.objects),
                    "initial_predicates": sorted(init_names),
                    "goal_predicates": sorted(goal_names),
                    "implicit_goal_conjunction": problem.implicit_goal_conjunction,
                }
            )
        except Exception as error:
            failures.append(
                {
                    "source_path": path.relative_to(args.activity_root).as_posix(),
                    "error": str(error),
                }
            )

    report = {
        "evidence_status": "source_audit_not_plan_validity_evidence",
        "activity_root": args.source_label or str(args.activity_root),
        "problem_file_count": len(paths),
        "parsed_count": len(records),
        "failure_count": len(failures),
        "implicit_goal_conjunction_count": sum(
            record["implicit_goal_conjunction"] for record in records
        ),
        "initial_predicate_problem_counts": _stable_counts(initial_counts),
        "goal_predicate_problem_counts": _stable_counts(goal_counts),
        "records": records,
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in report if key not in {"records", "failures"}}, indent=2))


if __name__ == "__main__":
    main()
