from scripts.filter_supported_action_queue import build_supported_queue


def test_filter_supported_queue_is_fail_closed_and_preserves_order():
    queue = {
        "queue_version": "source-v1",
        "records": [
            {"source_path": "a/problem0.bddl"},
            {"source_path": "b/problem0.bddl"},
            {"source_path": "c/problem0.bddl"},
        ],
    }
    audit = {
        "audit_version": "audit-v1",
        "tasks": [
            {"source_path": "c/problem0.bddl", "status": "candidate_supported_all_goal_alternatives"},
            {"source_path": "a/problem0.bddl", "status": "candidate_supported_all_goal_alternatives"},
            {"source_path": "b/problem0.bddl", "status": "candidate_unsupported", "errors": ["x"]},
        ],
    }
    result = build_supported_queue(queue, audit)
    assert [row["source_path"] for row in result["records"]] == [
        "a/problem0.bddl",
        "c/problem0.bddl",
    ]
    assert result["selected_count"] == 2
    assert result["excluded"] == [
        {"source_path": "b/problem0.bddl", "status": "candidate_unsupported", "errors": ["x"]}
    ]
