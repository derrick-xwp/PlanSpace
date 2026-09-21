"""Development-only action-domain adapters.

These adapters prove interfaces and tests. They are not the frozen paper
action domain and must not be used as benchmark evidence.
"""

from __future__ import annotations

from .bddl_parser import BDDLProblemDefinition
from .core import GroundAction, PlanningProblem, fact
from .translation import conjunctive_goal_facts, initial_facts


def opening_packages_problem(source: BDDLProblemDefinition) -> PlanningProblem:
    package_objects = [name for name, kind in source.objects if kind == "package.n.02"]
    if not package_objects:
        raise ValueError("opening_packages adapter found no package objects")
    actions = tuple(
        GroundAction(
            action_id=f"open::{package_name}",
            operator="OPEN",
            args=(package_name,),
            preconditions=frozenset({fact("not_open", package_name)}),
            add_effects=frozenset({fact("open", package_name)}),
            delete_effects=frozenset({fact("not_open", package_name)}),
        )
        for package_name in package_objects
    )
    return PlanningProblem(
        problem_id=source.problem_name,
        initial_state=initial_facts(source),
        goal=conjunctive_goal_facts(source),
        actions=actions,
    )

