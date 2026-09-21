"""Regression checks for equal-reference scoring and task-cluster summaries."""
import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts/analyze_matched_references.py"
spec = importlib.util.spec_from_file_location("matched", path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def ref(ids, edges=()):
    return {"action_ids": ids, "conservative_edges": edges, "relaxed_edges": edges}


def test_reference_count_and_order_are_separate():
    refs = [ref(["o", "a", "b"], [(0, 1), (0, 2)]), ref(["x"])]
    s = audit.matched_indices(["o", "b", "a"], True, refs)
    assert s["exact"] == [] and s["family"] == [0]
    other = audit.matched_indices(["x"], True, refs)
    assert other["exact"] == other["family"] == [1]
    bad = audit.matched_indices(["a", "o", "b"], True, refs)
    assert bad["family"] == [] and bad["multiset"] == [0]


def test_duplicate_occurrences_and_parse_failures():
    refs = [ref(["a", "b", "a"], [(0, 1), (1, 2)])]
    assert audit.matched_indices(["a", "b"], True, refs)["multiset"] == []
    assert audit.matched_indices(["a", "a", "b"], True, refs)["family"] == []
    assert all(not x for x in audit.matched_indices(["a", "b", "a"], False, refs).values())


def test_nested_reference_selection_and_fewer_than_k():
    assert audit.select_references(8, 19, 1) == audit.select_references(8, 19, 5)[:1]
    assert len(audit.select_references(2, 7, 5)) == 2
    assert set(audit.select_references(8, 41, "all")) == set(range(8))


def test_adjacent_swaps_are_not_label_filtered():
    assert list(audit.adjacent_swaps(["a", "a", "b"])) == [(1, ["a", "b", "a"])]
    assert len(list(audit.adjacent_swaps(["a", "b", "c"]))) == 2


def test_seed_averaging_does_not_multiply_denominator():
    rows = [{"task": "t", "valid": True, "designated_exact": False,
             "matches": {"exact": [], "family": [0], "relaxed": [0], "multiset": [0]}}]
    report = audit.aggregate(rows, {"t": [[0], [1], [0]]}, 100, 7)
    assert report["n"] == report["valid"] == 1
    assert abs(report["rules"]["family"]["valid_accepted"] - 2/3) < 1e-12
    assert report["rules"]["family"]["invalid_acceptance_pct"] is None
    assert report["rules"]["exact"]["valid_recall_pct"] == 0
