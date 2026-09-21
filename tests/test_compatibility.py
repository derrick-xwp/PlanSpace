from planspace.compatibility import (
    audit_selected_sources,
    finalize_review_queue,
    select_stratified_records,
    structural_candidates,
)


def _record(name, goals, objects=5):
    return {
        "problem_name": name,
        "source_path": f"{name}/problem0.bddl",
        "object_count": objects,
        "initial_predicates": ["inroom", "ontop"],
        "goal_predicates": goals,
        "implicit_goal_conjunction": False,
    }


def test_structural_filter_is_explicit_and_bounded():
    records = [
        _record("accepted", ["inside"]),
        _record("unsupported", ["covered"]),
        _record("too_large", ["open"], objects=21),
    ]
    assert [item["problem_name"] for item in structural_candidates(records)] == [
        "accepted"
    ]


def test_stratified_selection_is_deterministic_and_retains_rare_signature():
    records = [_record(f"inside_{index}", ["inside"]) for index in range(8)]
    records += [_record("rare_open", ["open"]), _record("rare_toggle", ["toggled_on"])]
    first, eligible = select_stratified_records(records, target_count=5)
    second, _ = select_stratified_records(reversed(records), target_count=5)
    assert eligible == 10
    assert first == second
    signatures = {tuple(item["goal_predicates"]) for item in first}
    assert ("open",) in signatures
    assert ("toggled_on",) in signatures


def test_selected_source_audit_reopens_and_compiles_fixture(tmp_path):
    source = """(define (problem tiny-0)
      (:domain omnigibson)
      (:objects apple_1 - apple.n.01 cabinet_1 - cabinet.n.01)
      (:init (ontop apple_1 cabinet_1))
      (:goal (inside apple_1 cabinet_1)))
    """
    activity = tmp_path / "tiny"
    activity.mkdir()
    (activity / "problem0.bddl").write_text(source)
    selected = [_record("tiny-0", ["inside"], objects=2)]
    selected[0]["source_path"] = "tiny/problem0.bddl"
    audited = audit_selected_sources(tmp_path, selected)
    assert audited[0]["translation_status"] == "pass"
    assert audited[0]["goal_alternative_count"] == 1
    assert audited[0]["required_action_motifs"] == ["PLACE_IN_OR_TRANSFER"]
    assert audited[0]["action_domain_status"] == "missing_or_unsigned"


def test_selected_source_audit_preserves_negative_goal_polarity(tmp_path):
    source = """(define (problem turn_off-0)
      (:domain omnigibson)
      (:objects lamp_1 - lamp.n.02)
      (:init (toggled_on lamp_1))
      (:goal (not (toggled_on lamp_1))))
    """
    activity = tmp_path / "turn_off"
    activity.mkdir()
    (activity / "problem0.bddl").write_text(source)
    selected = [_record("turn_off-0", ["toggled_on"], objects=1)]
    selected[0]["source_path"] = "turn_off/problem0.bddl"
    audited = audit_selected_sources(tmp_path, selected)
    assert audited[0]["translation_status"] == "pass"
    assert audited[0]["required_action_motifs"] == ["TOGGLE_OFF"]


def test_review_queue_excludes_translation_failures_and_is_deterministic():
    records = [_record(f"task_{index}", ["inside"]) for index in range(3)]
    screen = {"screen_version": "screen", "selected_records": records}
    audit_records = [
        {"source_path": records[0]["source_path"], "translation_status": "pass"},
        {"source_path": records[1]["source_path"], "translation_status": "fail"},
        {"source_path": records[2]["source_path"], "translation_status": "pass"},
    ]
    audit = {"audit_version": "audit", "records": audit_records}
    queue = finalize_review_queue(screen, audit, target_count=2)
    assert [record["problem_name"] for record in queue["records"]] == [
        "task_0",
        "task_2",
    ]
    assert queue["available_translation_pass_count"] == 2
