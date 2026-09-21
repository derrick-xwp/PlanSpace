from scripts.analyze_selection_coverage import analyze


def record(path, objects, goals):
    return {
        "source_path": path,
        "object_count": objects,
        "goal_predicates": goals,
        "implicit_goal_conjunction": False,
    }


def test_selection_funnel_and_exclusion_reasons_are_recomputed():
    records = [
        record("a", 2, ["inside"]),
        record("b", 3, ["inside"]),
        record("c", 30, ["inside"]),
        record("d", 2, ["covered"]),
    ]
    source = {"records": records}
    screen = {
        "eligible_count": 2,
        "selected_count": 2,
        "selected_records": records[:2],
        "rubric": {"supported_goal_predicates": ["inside"], "max_object_count": 20},
    }
    translation = {
        "records": [
            {"source_path": "a", "translation_status": "pass", "error": None},
            {"source_path": "b", "translation_status": "fail", "error": "bounded expansion"},
        ]
    }
    queue = {"selected_count": 1, "records": [{"source_path": "a"}]}
    report = analyze(source, screen, translation, queue)
    assert [row["count"] for row in report["funnel"]] == [4, 2, 2, 1, 1]
    assert report["structural_exclusion_reason_counts"] == {
        "object_count_above_limit": 1,
        "unsupported_goal_predicate": 1,
    }
    assert report["translation_failure_counts"] == {"bounded expansion": 1}
