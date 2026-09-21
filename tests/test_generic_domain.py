from planspace.bddl_parser import parse_problem_text
from planspace.core import execute_plan, fact
from planspace.domain_registry import get_generic_domain
from planspace.generic_domain import construct_goal_plan, generic_household_problem


def test_domain_registry_resolves_each_frozen_candidate_version():
    assert (
        get_generic_domain("planspace_generic_household_v0.1-candidate").GENERIC_DOMAIN_VERSION
        == "planspace_generic_household_v0.1-candidate"
    )
    assert (
        get_generic_domain("planspace_generic_household_v0.4-candidate").GENERIC_DOMAIN_VERSION
        == "planspace_generic_household_v0.4-candidate"
    )


def test_v01_domain_executes_its_own_frozen_action_type():
    source = parse_problem_text("""(define (problem windows-0)
      (:domain omnigibson)
      (:objects window_1 window_2 - openable_window.n.01)
      (:init (not (open window_1)) (not (open window_2)))
      (:goal (and (open window_1) (open window_2))))
    """)
    domain = get_generic_domain("planspace_generic_household_v0.1-candidate")
    problem = domain.generic_household_problem(source)
    plan = domain.construct_goal_plan(problem, problem.goal)
    assert [action.action_id for action in plan] == ["open::window_1", "open::window_2"]
    assert domain.execute_plan(problem, plan).valid


def test_closed_container_plan_opens_transfers_and_recloses():
    source = parse_problem_text("""(define (problem packing-0)
      (:domain omnigibson)
      (:objects apple_1 - apple.n.01 table_1 - table.n.02 box_1 - box.n.01)
      (:init (ontop apple_1 table_1) (not (open box_1)))
      (:goal (and (inside apple_1 box_1) (not (open box_1)))))
    """)
    problem = generic_household_problem(source)
    plan = construct_goal_plan(problem, problem.goal)
    assert [action.operator for action in plan] == ["OPEN", "TRANSFER", "CLOSE"]
    assert execute_plan(problem, plan).valid


def test_toggle_off_goal_uses_explicit_polarity():
    source = parse_problem_text("""(define (problem lights-0)
      (:domain omnigibson)
      (:objects lamp_1 - lamp.n.02)
      (:init (toggled_on lamp_1))
      (:goal (not (toggled_on lamp_1))))
    """)
    problem = generic_household_problem(source)
    plan = construct_goal_plan(problem, problem.goal)
    assert [action.operator for action in plan] == ["TOGGLE_OFF"]
    assert execute_plan(problem, plan).valid


def test_goal_polarity_uses_declared_selective_closed_world_completion():
    source = parse_problem_text("""(define (problem radio-0)
      (:domain omnigibson)
      (:objects radio_1 - radio.n.01)
      (:init)
      (:goal (toggled_on radio_1)))
    """)
    problem = generic_household_problem(source)
    assert next(iter(problem.actions)).operator == "TOGGLE_ON"
    assert execute_plan(problem, construct_goal_plan(problem, problem.goal)).valid


def test_room_membership_can_ground_a_transfer_source():
    source = parse_problem_text("""(define (problem chairs-0)
      (:domain omnigibson)
      (:objects chair_1 - chair.n.01 floor_1 - floor.n.01)
      (:init (inroom chair_1 living_room))
      (:goal (ontop chair_1 floor_1)))
    """)
    problem = generic_household_problem(source)
    plan = construct_goal_plan(problem, problem.goal)
    assert [action.operator for action in plan] == ["TRANSFER"]
    assert execute_plan(problem, plan).valid


def test_transfer_out_of_closed_controlled_container_recloses_it():
    source = parse_problem_text("""(define (problem mail-0)
      (:domain omnigibson)
      (:objects mail_1 - mail.n.04 mailbox_1 - mailbox.n.01 table_1 - table.n.02)
      (:init (inside mail_1 mailbox_1))
      (:goal (and (ontop mail_1 table_1) (not (open mailbox_1)))))
    """)
    problem = generic_household_problem(source)
    plan = construct_goal_plan(problem, problem.goal)
    assert [action.operator for action in plan] == ["OPEN", "TRANSFER", "CLOSE"]
    assert execute_plan(problem, plan).valid


def test_draped_clothing_is_a_supported_transfer_source():
    source = parse_problem_text("""(define (problem laundry-0)
      (:domain omnigibson)
      (:objects shirt_1 - shirt.n.01 rack_1 - coatrack.n.01 hamper_1 - hamper.n.02)
      (:init (draped shirt_1 rack_1))
      (:goal (inside shirt_1 hamper_1)))
    """)
    problem = generic_household_problem(source)
    plan = construct_goal_plan(problem, problem.goal)
    assert [action.operator for action in plan] == ["TRANSFER"]
    assert execute_plan(problem, plan).valid


def test_openable_class_is_gated_even_without_closed_goal():
    source = parse_problem_text("""(define (problem mail-0)
      (:domain omnigibson)
      (:objects mail_1 - mail.n.04 mailbox_1 - mailbox.n.01 table_1 - table.n.02)
      (:init (inside mail_1 mailbox_1))
      (:goal (ontop mail_1 table_1)))
    """)
    problem = generic_household_problem(source)
    transfer = next(action for action in problem.actions if action.operator == "TRANSFER")
    assert fact("open", "mailbox_1") in transfer.preconditions
    plan = construct_goal_plan(problem, problem.goal)
    assert [action.operator for action in plan] == ["OPEN", "TRANSFER"]


def test_reflexive_goal_bindings_and_actions_are_removed():
    source = parse_problem_text("""(define (problem disks-0)
      (:domain omnigibson)
      (:objects disk_1 disk_2 - videodisk.n.01 box_1 - carton.n.02)
      (:init (inside disk_1 box_1) (inside disk_2 box_1) (open box_1))
      (:goal (exists (?disk - videodisk.n.01) (ontop disk_1 ?disk))))
    """)
    problem = generic_household_problem(source)
    assert problem.goal_alternatives == (frozenset({fact("ontop", "disk_1", "disk_2")}),)
    assert all(action.args[0] != action.args[2] for action in problem.actions if action.operator == "TRANSFER")


def test_support_cycle_is_disabled_by_explicit_action_constraint():
    source = parse_problem_text("""(define (problem boxes-0)
      (:domain omnigibson)
      (:objects box_1 box_2 - storage_container.n.01 floor_1 - floor.n.01)
      (:init (ontop box_1 floor_1) (ontop box_2 floor_1))
      (:goal (or (ontop box_1 box_2) (ontop box_2 box_1))))
    """)
    problem = generic_household_problem(source)
    by_effect = {next(iter(action.add_effects)): action for action in problem.actions}
    first = by_effect[fact("ontop", "box_1", "box_2")]
    second = by_effect[fact("ontop", "box_2", "box_1")]
    state = first.apply(problem.initial_state)
    assert not second.enabled(state)
    result = execute_plan(problem, (first, second))
    assert result.constraint_violations == ("ontop_acyclic",)


def test_nested_container_destination_requires_open_outer_container():
    source = parse_problem_text("""(define (problem loading-0)
      (:domain omnigibson)
      (:objects camera_1 - digital_camera.n.01 container_1 - container.n.01
                car_1 - car.n.01 table_1 - table.n.02 floor_1 - floor.n.01)
      (:init (ontop camera_1 table_1) (ontop container_1 floor_1))
      (:goal (and (inside container_1 car_1) (inside camera_1 container_1)
                  (not (open car_1)))))
    """)
    problem = generic_household_problem(source)
    camera_transfer = next(
        action for action in problem.actions
        if fact("inside", "camera_1", "container_1") in action.add_effects
    )
    assert camera_transfer.enabled(problem.initial_state)
    by_id = {action.action_id: action for action in problem.actions}
    state = by_id["open::car_1"].apply(problem.initial_state)
    state = next(
        action for action in problem.actions
        if fact("inside", "container_1", "car_1") in action.add_effects
    ).apply(state)
    state = by_id["close::car_1"].apply(state)
    assert not camera_transfer.enabled(state)
    assert camera_transfer.required_open_containers(state) == frozenset({"car_1"})
    assert execute_plan(problem, construct_goal_plan(problem, problem.goal)).valid


def test_opening_nested_container_requires_open_outer_container_first():
    source = parse_problem_text("""(define (problem nested-0)
      (:domain omnigibson)
      (:objects food_1 - food.n.01 box_1 - pizza_box.n.01
                fridge_1 - electric_refrigerator.n.01 table_1 - table.n.02)
      (:init (inside food_1 box_1) (inside box_1 fridge_1))
      (:goal (ontop food_1 table_1)))
    """)
    problem = generic_household_problem(source)
    plan = construct_goal_plan(problem, problem.goal)
    assert [action.action_id for action in plan] == [
        "open::fridge_1",
        "open::box_1",
        "transfer::food_1::inside:box_1->ontop:table_1",
    ]
    assert execute_plan(problem, plan).valid
