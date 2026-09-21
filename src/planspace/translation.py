"""Versioned translation helpers from BDDL forms to PlanSpace predicates."""

from __future__ import annotations

from collections import defaultdict
from itertools import product

from .bddl_parser import BDDLProblemDefinition, SExpression
from .core import Predicate, fact


class UnsupportedGoalError(ValueError):
    pass


def goal_quantifier_diagnostics(problem: BDDLProblemDefinition) -> tuple[dict[str, str], ...]:
    """Return deterministic source-quality diagnostics without repairing intent."""

    diagnostics: list[dict[str, str]] = []

    def contains_symbol(expression: SExpression, symbol: str) -> bool:
        if isinstance(expression, str):
            return expression == symbol
        return any(contains_symbol(child, symbol) for child in expression)

    def visit(expression: SExpression) -> None:
        if isinstance(expression, str) or not expression:
            return
        head = expression[0]
        if head in {"forall", "exists"} and len(expression) == 3:
            for variable, variable_type in _typed_variables(expression[1]):
                if not contains_symbol(expression[2], variable):
                    diagnostics.append(
                        {
                            "kind": "vacuous_quantified_variable",
                            "quantifier": str(head),
                            "variable": variable,
                            "variable_type": variable_type,
                        }
                    )
            visit(expression[2])
            return
        for child in expression[1:]:
            visit(child)

    visit(problem.goal)
    return tuple(diagnostics)


def _tuple(expression: SExpression, label: str) -> tuple[SExpression, ...]:
    if isinstance(expression, str):
        raise ValueError(f"expected list for {label}")
    return expression


def _symbol(value: SExpression, environment: dict[str, str]) -> str:
    if not isinstance(value, str):
        raise ValueError("nested expression where a symbol was expected")
    if value in environment:
        return environment[value]
    return value[1:] if value.startswith("?") else value


def _atom(expression: SExpression, environment: dict[str, str]) -> Predicate:
    items = _tuple(expression, "predicate")
    if not items or not isinstance(items[0], str):
        raise ValueError("malformed predicate")
    return fact(items[0], *(_symbol(argument, environment) for argument in items[1:]))


def initial_facts(problem: BDDLProblemDefinition) -> frozenset[Predicate]:
    translated: set[Predicate] = set()
    for expression in problem.initial:
        items = _tuple(expression, "initial predicate")
        if items and items[0] == "not":
            if len(items) != 2:
                raise ValueError("malformed negated initial predicate")
            positive = _atom(items[1], {})
            translated.add(fact(f"not_{positive.name}", *positive.args))
        else:
            translated.add(_atom(expression, {}))
    return frozenset(translated)


def _typed_variables(declaration: SExpression) -> tuple[tuple[str, str], ...]:
    items = [item for item in _tuple(declaration, "quantifier declaration") if isinstance(item, str)]
    pending: list[str] = []
    result: list[tuple[str, str]] = []
    index = 0
    while index < len(items):
        token = items[index]
        if token != "-":
            pending.append(token)
            index += 1
            continue
        if not pending or index + 1 >= len(items):
            raise ValueError("malformed quantified variable declaration")
        variable_type = items[index + 1]
        result.extend((variable, variable_type) for variable in pending)
        pending.clear()
        index += 2
    if pending:
        raise ValueError("untyped quantified variable")
    return tuple(result)


def conjunctive_goal_facts(problem: BDDLProblemDefinition) -> frozenset[Predicate]:
    """Return a goal only when grounding produces one conjunction.

    Call :func:`goal_alternatives` when disjunctions or existential witnesses
    are allowed by the action-domain adapter.
    """

    alternatives = goal_alternatives(problem)
    if len(alternatives) != 1:
        raise UnsupportedGoalError(
            f"goal has {len(alternatives)} grounded alternatives, not one conjunction"
        )
    return alternatives[0]


def goal_alternatives(
    problem: BDDLProblemDefinition, *, max_alternatives: int = 10000
) -> tuple[frozenset[Predicate], ...]:
    """Compile finite BDDL goal logic into explicit DNF alternatives.

    Conjunction and universal quantification form Cartesian products;
    disjunction and existential quantification form unions. The explicit cap
    prevents an unnoticed combinatorial explosion during source translation.
    """

    objects_by_type: dict[str, list[str]] = defaultdict(list)
    for object_name, object_type in problem.objects:
        objects_by_type[object_type].append(object_name)

    def checked(
        alternatives: list[frozenset[Predicate]], label: str
    ) -> tuple[frozenset[Predicate], ...]:
        unique = tuple(dict.fromkeys(alternatives))
        if len(unique) > max_alternatives:
            raise UnsupportedGoalError(
                f"{label} expands to more than {max_alternatives} goal alternatives"
            )
        return unique

    def combine(
        left: tuple[frozenset[Predicate], ...],
        right: tuple[frozenset[Predicate], ...],
    ) -> tuple[frozenset[Predicate], ...]:
        return checked(
            [left_goal | right_goal for left_goal, right_goal in product(left, right)],
            "conjunctive goal",
        )

    def quantified_environments(
        declaration: SExpression, environment: dict[str, str]
    ) -> tuple[dict[str, str], ...]:
        environments = [dict(environment)]
        for variable, variable_type in _typed_variables(declaration):
            objects = objects_by_type.get(variable_type, [])
            if not objects:
                raise UnsupportedGoalError(
                    f"no objects found for quantified type {variable_type}"
                )
            environments = [
                {**current, variable: object_name}
                for current in environments
                for object_name in objects
            ]
        return tuple(environments)

    def visit(
        expression: SExpression, environment: dict[str, str]
    ) -> tuple[frozenset[Predicate], ...]:
        items = _tuple(expression, "goal")
        if not items or not isinstance(items[0], str):
            raise ValueError("malformed goal expression")
        head = items[0]
        if head == "and":
            result = (frozenset(),)
            for child in items[1:]:
                result = combine(result, visit(child, environment))
            return result
        if head == "or":
            alternatives: list[frozenset[Predicate]] = []
            for child in items[1:]:
                alternatives.extend(visit(child, environment))
            return checked(alternatives, "disjunctive goal")
        if head in {"forall", "exists"}:
            if len(items) != 3:
                raise UnsupportedGoalError(f"only one-body {head} goals are supported")
            environments = quantified_environments(items[1], environment)
            if head == "exists":
                alternatives = []
                for grounded_environment in environments:
                    alternatives.extend(visit(items[2], grounded_environment))
                return checked(alternatives, "existential goal")
            result = (frozenset(),)
            for grounded_environment in environments:
                result = combine(result, visit(items[2], grounded_environment))
            return result
        if head in {"forpairs", "forn", "imply"}:
            raise UnsupportedGoalError(f"unsupported non-conjunctive goal operator: {head}")
        if head == "not":
            if len(items) != 2:
                raise ValueError("malformed negated goal")
            positive = _atom(items[1], environment)
            return (frozenset({fact(f"not_{positive.name}", *positive.args)}),)
        return (frozenset({_atom(expression, environment)}),)

    alternatives = visit(problem.goal, {})
    if not alternatives:
        raise UnsupportedGoalError("goal expands to no alternatives")
    return alternatives
