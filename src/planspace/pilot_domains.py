"""Candidate action semantics for frozen-source pilot tasks.

These adapters are versioned and testable, but their outputs remain excluded
from paper claims until the trace-level faithfulness audit is complete.
"""

from __future__ import annotations

from .bddl_parser import BDDLProblemDefinition
from .core import GroundAction, PlanningProblem, Predicate, fact
from .translation import goal_alternatives, initial_facts


ACTION_DOMAIN_VERSION = "planspace_domain_v0.2-candidate"


def _facts_named(facts: frozenset[Predicate], name: str) -> tuple[Predicate, ...]:
    return tuple(item for item in facts if item.name == name)


def opening_doors_problem(source: BDDLProblemDefinition) -> PlanningProblem:
    """Translate `opening_doors` with explicit room-to-room navigation."""

    state = initial_facts(source)
    agents = [name for name, kind in source.objects if kind == "agent.n.01"]
    doors = [name for name, kind in source.objects if kind == "door.n.01"]
    if len(agents) != 1 or not doors:
        raise ValueError("opening_doors requires one agent and at least one door")
    agent = agents[0]

    room_by_object = {
        predicate.args[0]: predicate.args[1]
        for predicate in _facts_named(state, "inroom")
        if len(predicate.args) == 2
    }
    support_by_agent = {
        predicate.args[0]: predicate.args[1]
        for predicate in _facts_named(state, "ontop")
        if len(predicate.args) == 2
    }
    support = support_by_agent.get(agent)
    initial_room = room_by_object.get(support or "")
    if initial_room is None:
        raise ValueError("cannot infer the agent's initial room")

    door_rooms = {door: room_by_object.get(door) for door in doors}
    if any(room is None for room in door_rooms.values()):
        raise ValueError("every door must have an inroom predicate")
    rooms = tuple(sorted(set(door_rooms.values())))
    state = state | {fact("agent_inroom", agent, initial_room)}

    actions: list[GroundAction] = []
    for source_room in rooms:
        for destination_room in rooms:
            if source_room == destination_room:
                continue
            actions.append(
                GroundAction(
                    action_id=f"navigate::{source_room}->{destination_room}",
                    operator="NAVIGATE",
                    args=(agent, source_room, destination_room),
                    preconditions=frozenset(
                        {fact("agent_inroom", agent, source_room)}
                    ),
                    add_effects=frozenset(
                        {fact("agent_inroom", agent, destination_room)}
                    ),
                    delete_effects=frozenset(
                        {fact("agent_inroom", agent, source_room)}
                    ),
                )
            )
    for door in doors:
        room = door_rooms[door]
        actions.append(
            GroundAction(
                action_id=f"open::{door}",
                operator="OPEN",
                args=(door,),
                preconditions=frozenset(
                    {
                        fact("agent_inroom", agent, room),
                        fact("not_open", door),
                    }
                ),
                add_effects=frozenset({fact("open", door)}),
                delete_effects=frozenset({fact("not_open", door)}),
            )
        )

    alternatives = goal_alternatives(source)
    return PlanningProblem(
        problem_id=source.problem_name,
        initial_state=frozenset(state),
        goal=alternatives[0],
        actions=tuple(actions),
        goal_alternatives=alternatives,
    )


def installing_a_printer_problem(source: BDDLProblemDefinition) -> PlanningProblem:
    """Translate `installing_a_printer` with one high-level transfer skill."""

    state = initial_facts(source)
    printers = [name for name, kind in source.objects if kind == "printer.n.03"]
    tables = [name for name, kind in source.objects if kind == "table.n.02"]
    agents = [name for name, kind in source.objects if kind == "agent.n.01"]
    if len(printers) != 1 or len(tables) != 1 or len(agents) != 1:
        raise ValueError("installing_a_printer requires one printer, table and agent")
    printer, table, agent = printers[0], tables[0], agents[0]

    supports = {
        predicate.args[0]: predicate.args[1]
        for predicate in _facts_named(state, "ontop")
        if len(predicate.args) == 2
    }
    source_support = supports.get(printer)
    if source_support is None:
        raise ValueError("printer requires an initial ontop support")

    actions = (
        GroundAction(
            action_id=f"transfer::{printer}::{source_support}->{table}",
            operator="TRANSFER",
            args=(printer, source_support, table),
            preconditions=frozenset({fact("ontop", printer, source_support)}),
            add_effects=frozenset({fact("ontop", printer, table)}),
            delete_effects=frozenset({fact("ontop", printer, source_support)}),
        ),
        GroundAction(
            action_id=f"toggle_on::{printer}",
            operator="TOGGLE_ON",
            args=(agent, printer),
            preconditions=frozenset(
                {
                    fact("not_toggled_on", printer),
                    fact("ontop", printer, table),
                }
            ),
            add_effects=frozenset({fact("toggled_on", printer)}),
            delete_effects=frozenset({fact("not_toggled_on", printer)}),
        ),
    )
    alternatives = goal_alternatives(source)
    return PlanningProblem(
        problem_id=source.problem_name,
        initial_state=frozenset(state),
        goal=alternatives[0],
        actions=actions,
        goal_alternatives=alternatives,
    )


def organizing_file_cabinet_problem(
    source: BDDLProblemDefinition,
) -> PlanningProblem:
    """Translate already-local object moves as atomic candidate transfers.

    The task takes place in one room. Objects whose desired relation already
    holds are deliberately omitted, making partial initial satisfaction
    explicit rather than generating redundant actions.
    """

    state = initial_facts(source)
    alternatives = goal_alternatives(source)
    if len(alternatives) != 1:
        raise ValueError("organizing_file_cabinet requires one conjunctive goal")

    current_relations = {
        predicate.args[0]: predicate
        for predicate in state
        if predicate.name in {"inside", "ontop"} and len(predicate.args) == 2
    }
    actions: list[GroundAction] = []
    for desired in sorted(alternatives[0]):
        if desired in state:
            continue
        if desired.name not in {"inside", "ontop"} or len(desired.args) != 2:
            raise ValueError(f"unsupported cabinet goal predicate: {desired}")
        object_name, target = desired.args
        current = current_relations.get(object_name)
        if current is None:
            raise ValueError(f"cannot infer current support for {object_name}")
        source_support = current.args[1]
        actions.append(
            GroundAction(
                action_id=(
                    f"transfer::{object_name}::"
                    f"{current.name}:{source_support}->{desired.name}:{target}"
                ),
                operator="TRANSFER",
                args=(object_name, source_support, target),
                preconditions=frozenset({current}),
                add_effects=frozenset({desired}),
                delete_effects=frozenset({current}),
            )
        )

    return PlanningProblem(
        problem_id=source.problem_name,
        initial_state=state,
        goal=alternatives[0],
        actions=tuple(actions),
        goal_alternatives=alternatives,
    )


def moving_boxes_to_storage_problem(
    source: BDDLProblemDefinition,
) -> PlanningProblem:
    """Translate two-box storage as garage moves followed by stacking."""

    state = initial_facts(source)
    alternatives = goal_alternatives(source)
    boxes = [
        name for name, kind in source.objects if kind == "storage_container.n.01"
    ]
    floors = [name for name, kind in source.objects if kind == "floor.n.01"]
    if len(boxes) != 2 or len(floors) != 2 or len(alternatives) != 2:
        raise ValueError(
            "moving_boxes_to_storage requires two boxes, two floors and two goals"
        )

    room_by_floor = {
        predicate.args[0]: predicate.args[1]
        for predicate in _facts_named(state, "inroom")
        if len(predicate.args) == 2
    }
    living_floors = [floor for floor in floors if room_by_floor.get(floor) == "living_room"]
    garage_floors = [floor for floor in floors if room_by_floor.get(floor) == "garage"]
    if len(living_floors) != 1 or len(garage_floors) != 1:
        raise ValueError("cannot identify one living-room floor and one garage floor")
    living_floor, garage_floor = living_floors[0], garage_floors[0]

    actions: list[GroundAction] = []
    for box in boxes:
        actions.append(
            GroundAction(
                action_id=f"move_to_garage::{box}",
                operator="TRANSFER",
                args=(box, living_floor, garage_floor),
                preconditions=frozenset({fact("ontop", box, living_floor)}),
                add_effects=frozenset({fact("ontop", box, garage_floor)}),
                delete_effects=frozenset({fact("ontop", box, living_floor)}),
            )
        )

    for top in boxes:
        bottom = next(box for box in boxes if box != top)
        for source_support in (living_floor, garage_floor):
            actions.append(
                GroundAction(
                    action_id=f"stack::{top}->{bottom}::from:{source_support}",
                    operator="TRANSFER",
                    args=(top, bottom, source_support),
                    preconditions=frozenset(
                        {
                            fact("ontop", top, source_support),
                            fact("ontop", bottom, garage_floor),
                        }
                    ),
                    add_effects=frozenset({fact("ontop", top, bottom)}),
                    delete_effects=frozenset({fact("ontop", top, source_support)}),
                )
            )

    return PlanningProblem(
        problem_id=source.problem_name,
        initial_state=state,
        goal=alternatives[0],
        actions=tuple(actions),
        goal_alternatives=alternatives,
    )


def storing_food_problem(source: BDDLProblemDefinition) -> PlanningProblem:
    """Translate independent food-item storage with two cabinet witnesses."""

    state = initial_facts(source)
    alternatives = goal_alternatives(source)
    cabinets = [name for name, kind in source.objects if kind == "cabinet.n.01"]
    if len(cabinets) != 2 or len(alternatives) != 256:
        raise ValueError("storing_food requires two cabinets and 256 goal alternatives")

    goal_facts = set().union(*alternatives)
    items = sorted(
        {
            predicate.args[0]
            for predicate in goal_facts
            if predicate.name == "inside" and len(predicate.args) == 2
        }
    )
    if len(items) != 8:
        raise ValueError("storing_food requires eight goal items")

    supports = {
        predicate.args[0]: predicate.args[1]
        for predicate in _facts_named(state, "ontop")
        if len(predicate.args) == 2
    }
    actions: list[GroundAction] = []
    for item in items:
        source_support = supports.get(item)
        if source_support is None:
            raise ValueError(f"cannot infer initial support for {item}")
        for cabinet in sorted(cabinets):
            actions.append(
                GroundAction(
                    action_id=f"store::{item}->{cabinet}",
                    operator="TRANSFER",
                    args=(item, source_support, cabinet),
                    preconditions=frozenset({fact("ontop", item, source_support)}),
                    add_effects=frozenset({fact("inside", item, cabinet)}),
                    delete_effects=frozenset({fact("ontop", item, source_support)}),
                )
            )

    return PlanningProblem(
        problem_id=source.problem_name,
        initial_state=state,
        goal=alternatives[0],
        actions=tuple(actions),
        goal_alternatives=alternatives,
    )
