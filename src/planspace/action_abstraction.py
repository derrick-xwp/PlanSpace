"""Versioned action-abstraction contract and pilot consistency audit."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .core import PlanningProblem


ACTION_ABSTRACTION_VERSION = "planspace_high_level_skills_v0.1-candidate"
CANONICAL_OPERATORS = frozenset(
    {"NAVIGATE", "OPEN", "CLOSE", "TRANSFER", "TOGGLE_ON", "TOGGLE_OFF"}
)
OPERATOR_ALIASES = {
    "MOVE_TO_GARAGE": "TRANSFER",
    "PLACE_ON": "TRANSFER",
    "STACK": "TRANSFER",
    "STORE": "TRANSFER",
}
LOW_LEVEL_PRIMITIVES = frozenset({"GRASP"})


@dataclass(frozen=True)
class ActionAbstractionAudit:
    task: str
    operators: tuple[str, ...]
    canonical_operators: tuple[str, ...]
    status: str
    required_change: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def audit_action_abstraction(
    task: str, problem: PlanningProblem
) -> ActionAbstractionAudit:
    """Classify a pilot adapter against the primary high-level-skill track.

    This is a structural consistency check, not semantic approval.  In
    particular, it cannot establish that an atomic transfer is physically
    feasible or faithful to the source task.
    """

    operators = tuple(sorted({action.operator for action in problem.actions}))
    unknown = sorted(
        operator
        for operator in operators
        if operator not in CANONICAL_OPERATORS
        and operator not in OPERATOR_ALIASES
        and operator not in LOW_LEVEL_PRIMITIVES
    )
    primitives = sorted(set(operators) & LOW_LEVEL_PRIMITIVES)
    aliases = sorted(set(operators) & set(OPERATOR_ALIASES))
    canonical = tuple(
        sorted(
            {
                OPERATOR_ALIASES.get(operator, operator)
                for operator in operators
                if operator not in LOW_LEVEL_PRIMITIVES
                and operator not in unknown
            }
        )
    )

    if unknown:
        status = "unsupported_operator"
        required_change = "Define or remove unsupported operators: " + ", ".join(unknown)
    elif primitives:
        status = "granularity_rewrite_required"
        required_change = (
            "Replace split motor-level primitives with one grounded TRANSFER skill: "
            + ", ".join(primitives)
        )
    elif aliases:
        status = "canonical_naming_rewrite_required"
        required_change = "Normalize aliases: " + ", ".join(
            f"{operator}->{OPERATOR_ALIASES[operator]}" for operator in aliases
        )
    else:
        status = "structurally_compliant_pending_semantic_review"
        required_change = "None structurally; independent semantic review remains required."

    return ActionAbstractionAudit(
        task=task,
        operators=operators,
        canonical_operators=canonical,
        status=status,
        required_change=required_change,
    )


def summarize_action_abstraction(
    problems: Iterable[tuple[str, PlanningProblem]],
) -> tuple[ActionAbstractionAudit, ...]:
    return tuple(audit_action_abstraction(task, problem) for task, problem in problems)
