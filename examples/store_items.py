"""Small deterministic task with two valid action interleavings."""

from planspace.core import GroundAction, PlanningProblem, fact


def build_problem() -> tuple[PlanningProblem, tuple[GroundAction, ...], tuple[GroundAction, ...]]:
    cabinet = "cabinet_1"
    apple = "apple_1"
    counter = "counter_1"

    closed = fact("closed", cabinet)
    opened = fact("open", cabinet)
    on_counter = fact("on", apple, counter)
    holding = fact("holding", apple)
    hand_empty = fact("hand_empty", "agent_1")
    inside = fact("inside", apple, cabinet)

    open_cabinet = GroundAction(
        action_id="open_cabinet",
        operator="OPEN",
        args=(cabinet,),
        preconditions=frozenset({closed}),
        add_effects=frozenset({opened}),
        delete_effects=frozenset({closed}),
    )
    grasp_apple = GroundAction(
        action_id="grasp_apple",
        operator="GRASP",
        args=(apple,),
        preconditions=frozenset({on_counter, hand_empty}),
        add_effects=frozenset({holding}),
        delete_effects=frozenset({on_counter, hand_empty}),
    )
    place_apple = GroundAction(
        action_id="place_apple",
        operator="PLACE_IN",
        args=(apple, cabinet),
        preconditions=frozenset({holding, opened}),
        add_effects=frozenset({inside, hand_empty}),
        delete_effects=frozenset({holding}),
    )
    close_cabinet = GroundAction(
        action_id="close_cabinet",
        operator="CLOSE",
        args=(cabinet,),
        preconditions=frozenset({opened}),
        add_effects=frozenset({closed}),
        delete_effects=frozenset({opened}),
    )

    problem = PlanningProblem(
        problem_id="synthetic_store_items_0001",
        initial_state=frozenset({closed, on_counter, hand_empty}),
        goal=frozenset({inside, closed}),
        actions=(open_cabinet, grasp_apple, place_apple, close_cabinet),
    )
    plan_a = (open_cabinet, grasp_apple, place_apple, close_cabinet)
    plan_b = (grasp_apple, open_cabinet, place_apple, close_cabinet)
    return problem, plan_a, plan_b

