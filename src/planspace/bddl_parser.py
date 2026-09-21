"""Small dependency-free reader for the BDDL problem subset used by PlanSpace.

The parser preserves logical structure. It does not interpret BDDL predicates
as PlanSpace action semantics; that translation is a separate, versioned step.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Union


SExpression = Union[str, tuple["SExpression", ...]]


def _tokenize(text: str) -> list[str]:
    without_comments = re.sub(r";[^\n]*", "", text)
    return re.findall(r"\(|\)|[^\s()]+", without_comments)


def parse_sexpression(text: str) -> SExpression:
    tokens = _tokenize(text)
    position = 0

    def parse_one() -> SExpression:
        nonlocal position
        if position >= len(tokens):
            raise ValueError("unexpected end of BDDL input")
        token = tokens[position]
        position += 1
        if token == "(":
            children: list[SExpression] = []
            while position < len(tokens) and tokens[position] != ")":
                children.append(parse_one())
            if position >= len(tokens):
                raise ValueError("unclosed BDDL list")
            position += 1
            return tuple(children)
        if token == ")":
            raise ValueError("unexpected closing parenthesis")
        return token

    root = parse_one()
    if position != len(tokens):
        raise ValueError("multiple top-level BDDL expressions")
    return root


@dataclass(frozen=True)
class BDDLProblemDefinition:
    problem_name: str
    domain_name: str
    objects: tuple[tuple[str, str], ...]
    initial: tuple[SExpression, ...]
    goal: SExpression
    source_path: str | None = None
    implicit_goal_conjunction: bool = False


def _as_list(expression: SExpression, label: str) -> tuple[SExpression, ...]:
    if isinstance(expression, str):
        raise ValueError(f"expected list for {label}")
    return expression


def _section(define: tuple[SExpression, ...], name: str) -> tuple[SExpression, ...]:
    for child in define:
        if isinstance(child, tuple) and child and child[0] == name:
            return child
    raise ValueError(f"missing BDDL section {name}")


def _parse_objects(tokens: tuple[SExpression, ...]) -> tuple[tuple[str, str], ...]:
    flat = [item for item in tokens if isinstance(item, str)]
    objects: list[tuple[str, str]] = []
    pending: list[str] = []
    index = 0
    while index < len(flat):
        token = flat[index]
        if token != "-":
            pending.append(token)
            index += 1
            continue
        if not pending or index + 1 >= len(flat):
            raise ValueError("malformed typed object declaration")
        object_type = flat[index + 1]
        objects.extend((object_name, object_type) for object_name in pending)
        pending.clear()
        index += 2
    if pending:
        raise ValueError("untyped BDDL objects are not supported")
    return tuple(objects)


def parse_problem_text(text: str, *, source_path: str | None = None) -> BDDLProblemDefinition:
    root = _as_list(parse_sexpression(text), "root")
    if not root or root[0] != "define":
        raise ValueError("expected a BDDL define form")
    problem_form = _as_list(root[1], "problem declaration")
    domain_form = _section(root, ":domain")
    object_form = _section(root, ":objects")
    init_form = _section(root, ":init")
    goal_form = _section(root, ":goal")
    if len(problem_form) != 2 or problem_form[0] != "problem":
        raise ValueError("malformed BDDL problem declaration")
    if len(domain_form) != 2 or not isinstance(domain_form[1], str):
        raise ValueError("malformed BDDL domain declaration")
    if len(goal_form) < 2:
        raise ValueError("expected at least one BDDL goal expression")
    implicit_goal_conjunction = len(goal_form) > 2
    goal = (
        ("and", *goal_form[1:])
        if implicit_goal_conjunction
        else goal_form[1]
    )
    return BDDLProblemDefinition(
        problem_name=str(problem_form[1]),
        domain_name=domain_form[1],
        objects=_parse_objects(object_form[1:]),
        initial=tuple(init_form[1:]),
        goal=goal,
        source_path=source_path,
        implicit_goal_conjunction=implicit_goal_conjunction,
    )


def parse_problem_file(path: str | Path) -> BDDLProblemDefinition:
    source = Path(path)
    return parse_problem_text(source.read_text(encoding="utf-8"), source_path=str(source))


def predicate_names(expression: SExpression) -> frozenset[str]:
    logical = {"and", "or", "not", "exists", "forall", "forpairs", "forn"}
    names: set[str] = set()

    def visit(node: SExpression) -> None:
        if isinstance(node, str) or not node:
            return
        head = node[0]
        if (
            isinstance(head, str)
            and head not in logical
            and not head.startswith((":", "?"))
            and not head.isdigit()
        ):
            names.add(head)
        for child in node[1:]:
            visit(child)

    visit(expression)
    return frozenset(names)
