"""Candidate generic high-level action domain for the frozen 100-task queue."""

from __future__ import annotations

from .bddl_parser import BDDLProblemDefinition
from .core import GroundAction, PlanningProblem, Predicate, fact
from .translation import goal_alternatives, initial_facts
from .core import execute_plan
from .partial_order import dependency_edges


GENERIC_DOMAIN_VERSION = "planspace_generic_household_v0.4-candidate"

GATED_CONTAINER_TYPES = frozenset(
    {
        "cabinet.n.01",
        "car.n.01",
        "carton.n.02",
        "clothes_dryer.n.01",
        "dishwasher.n.01",
        "electric_refrigerator.n.01",
        "mailbox.n.01",
        "pizza_box.n.01",
        "recycling_bin.n.01",
        "toolbox.n.01",
        "tupperware.n.01",
        "washer.n.03",
    }
)


class UnsupportedGenericDomain(ValueError):
    pass


def _action(
    action_id: str,
    operator: str,
    args: tuple[str, ...],
    preconditions: set[Predicate],
    add_effects: set[Predicate],
    delete_effects: set[Predicate],
    constraints: tuple[str, ...] = (),
    access_sources: tuple[str, ...] = (),
    access_targets: tuple[str, ...] = (),
    gated_containers: frozenset[str] = frozenset(),
) -> GroundAction:
    return GroundAction(
        action_id=action_id,
        operator=operator,
        args=args,
        preconditions=frozenset(preconditions),
        add_effects=frozenset(add_effects),
        delete_effects=frozenset(delete_effects),
        constraints=constraints,
        access_sources=access_sources,
        access_targets=access_targets,
        gated_containers=gated_containers,
    )


def generic_household_problem(source: BDDLProblemDefinition) -> PlanningProblem:
    """Compile supported goal facts into candidate high-level skills.

    The adapter is intentionally conservative.  It rejects a desired relation
    when the object's frozen source support cannot be identified, and it models
    openable target containers only when their initial polarity is explicit.
    """

    state = set(initial_facts(source))
    def spatially_consistent(alternative: frozenset[Predicate]) -> bool:
        spatial = [
            predicate
            for predicate in alternative
            if predicate.name in {"inside", "ontop", "inroom", "onfloor", "draped"}
            and len(predicate.args) == 2
        ]
        if any(predicate.args[0] == predicate.args[1] for predicate in spatial):
            return False
        return len({predicate.args[0] for predicate in spatial}) == len(spatial)

    alternatives = tuple(
        alternative
        for alternative in goal_alternatives(source)
        if spatially_consistent(alternative)
    )
    if not alternatives:
        raise UnsupportedGenericDomain("all grounded goals violate spatial irreflexivity")
    desired = set().union(*alternatives)
    supported = {
        "inside",
        "ontop",
        "open",
        "not_open",
        "toggled_on",
        "not_toggled_on",
    }
    unknown = sorted({predicate.name for predicate in desired} - supported)
    if unknown:
        raise UnsupportedGenericDomain("unsupported goal facts: " + ", ".join(unknown))

    controlled_openables = {
        object_name
        for object_name, object_type in source.objects
        if object_type in GATED_CONTAINER_TYPES
    } | {
        predicate.args[0]
        for predicate in state | desired
        if predicate.name in {"open", "not_open"} and len(predicate.args) == 1
    }
    controlled_toggles = {
        predicate.args[0]
        for predicate in desired
        if predicate.name in {"toggled_on", "not_toggled_on"}
        and len(predicate.args) == 1
    }
    for object_name in controlled_openables:
        if (
            fact("open", object_name) not in state
            and fact("not_open", object_name) not in state
        ):
            state.add(fact("not_open", object_name))
    for object_name in controlled_toggles:
        if (
            fact("toggled_on", object_name) not in state
            and fact("not_toggled_on", object_name) not in state
        ):
            state.add(fact("not_toggled_on", object_name))
    state = frozenset(state)

    actions: dict[str, GroundAction] = {}
    desired_closed = {
        predicate.args[0]
        for predicate in desired
        if predicate.name == "not_open" and len(predicate.args) == 1
    }
    inside_targets = {
        predicate.args[1]
        for predicate in desired
        if predicate.name == "inside"
        and len(predicate.args) == 2
        and predicate not in state
    }
    def add_open(object_name: str) -> None:
        closed = fact("not_open", object_name)
        opened = fact("open", object_name)
        if closed not in state:
            return
        action_id = f"open::{object_name}"
        actions[action_id] = _action(
            action_id,
            "OPEN",
            (object_name,),
            {closed},
            {opened},
            {closed},
            ("open_access_chains",),
            (object_name,),
            (),
            frozenset(controlled_openables),
        )

    def add_close(object_name: str) -> None:
        opened = fact("open", object_name)
        closed = fact("not_open", object_name)
        if opened not in state and object_name not in controlled_openables:
            return
        action_id = f"close::{object_name}"
        actions[action_id] = _action(
            action_id,
            "CLOSE",
            (object_name,),
            {opened},
            {closed},
            {opened},
            ("open_access_chains",),
            (object_name,),
            (),
            frozenset(controlled_openables),
        )

    for object_name in sorted(controlled_openables):
        add_open(object_name)

    for predicate in sorted(desired):
        if predicate.name == "open" and predicate not in state:
            add_open(predicate.args[0])
        elif predicate.name == "not_open" and predicate not in state:
            add_close(predicate.args[0])
        elif predicate.name == "toggled_on" and predicate not in state:
            object_name = predicate.args[0]
            off = fact("not_toggled_on", object_name)
            if off not in state:
                raise UnsupportedGenericDomain(f"missing toggle polarity for {object_name}")
            action_id = f"toggle_on::{object_name}"
            actions[action_id] = _action(
                action_id,
                "TOGGLE_ON",
                (object_name,),
                {off},
                {predicate},
                {off},
                ("open_access_chains",),
                (object_name,),
                (),
                frozenset(controlled_openables),
            )
        elif predicate.name == "not_toggled_on" and predicate not in state:
            object_name = predicate.args[0]
            on = fact("toggled_on", object_name)
            if on not in state:
                raise UnsupportedGenericDomain(f"missing toggle polarity for {object_name}")
            action_id = f"toggle_off::{object_name}"
            actions[action_id] = _action(
                action_id,
                "TOGGLE_OFF",
                (object_name,),
                {on},
                {predicate},
                {on},
                ("open_access_chains",),
                (object_name,),
                (),
                frozenset(controlled_openables),
            )

    initial_relations: dict[str, list[Predicate]] = {}
    for predicate in state:
        if predicate.name in {"inside", "ontop", "inroom", "onfloor", "draped"} and len(predicate.args) == 2:
            initial_relations.setdefault(predicate.args[0], []).append(predicate)

    for predicate in sorted(desired):
        if predicate.name not in {"inside", "ontop"} or predicate in state:
            continue
        if len(predicate.args) != 2:
            raise UnsupportedGenericDomain(f"malformed relation goal: {predicate}")
        object_name, target = predicate.args
        sources = sorted(
            relation
            for relation in initial_relations.get(object_name, [])
            if relation != predicate
        )
        if len(sources) != 1:
            raise UnsupportedGenericDomain(
                f"expected one frozen source relation for {object_name}, found {len(sources)}"
            )
        source_relation = sources[0]
        preconditions = {source_relation}
        if (
            source_relation.name == "inside"
            and source_relation.args[1] in controlled_openables
        ):
            source_container = source_relation.args[1]
            preconditions.add(fact("open", source_container))
            add_open(source_container)
            if source_container in desired_closed:
                add_close(source_container)
        if predicate.name == "inside":
            opened = fact("open", target)
            closed = fact("not_open", target)
            if target in controlled_openables:
                preconditions.add(opened)
            if closed in state:
                add_open(target)
            if target in desired_closed:
                add_close(target)
        action_id = (
            f"transfer::{object_name}::{source_relation.name}:{source_relation.args[1]}"
            f"->{predicate.name}:{target}"
        )
        actions[action_id] = _action(
            action_id,
            "TRANSFER",
            (object_name, source_relation.args[1], target),
            preconditions,
            {predicate},
            {source_relation},
            (
                "spatial_irreflexive",
                "spatial_unique_location",
                "ontop_acyclic",
                "open_access_chains",
            ),
            (object_name,),
            (target,),
            frozenset(controlled_openables),
        )

    return PlanningProblem(
        problem_id=source.problem_name,
        initial_state=state,
        goal=alternatives[0],
        actions=tuple(actions[key] for key in sorted(actions)),
        goal_alternatives=alternatives,
    )


def construct_goal_plan(
    problem: PlanningProblem, goal: frozenset[Predicate]
) -> tuple[GroundAction, ...]:
    """Construct a deterministic causal plan for one grounded goal alternative."""

    state = problem.initial_state
    plan: list[GroundAction] = []
    active: set[Predicate] = set()

    def achieve(predicate: Predicate) -> None:
        nonlocal state
        if predicate in state:
            return
        if predicate in active:
            raise UnsupportedGenericDomain(f"cyclic support while achieving {predicate}")
        active.add(predicate)
        producers = sorted(
            (action for action in problem.actions if predicate in action.add_effects),
            key=lambda action: action.action_id,
        )
        if not producers:
            raise UnsupportedGenericDomain(f"no action can achieve {predicate}")
        action = producers[0]
        for precondition in sorted(action.preconditions):
            achieve(precondition)
        for container in sorted(action.required_open_containers(state)):
            achieve(fact("open", container))
        if not action.enabled(state):
            raise UnsupportedGenericDomain(f"unresolved preconditions for {action.action_id}")
        state = action.apply(state)
        plan.append(action)
        active.remove(predicate)

    positive = sorted(
        (predicate for predicate in goal if not predicate.name.startswith("not_"))
    )
    negative = sorted(
        (predicate for predicate in goal if predicate.name.startswith("not_"))
    )
    for predicate in positive:
        achieve(predicate)
    for predicate in negative:
        achieve(predicate)
    if not goal <= state:
        missing = ", ".join(map(str, sorted(goal - state)))
        raise UnsupportedGenericDomain(f"constructed plan does not preserve goal: {missing}")
    return tuple(plan)
