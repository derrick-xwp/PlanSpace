import json
from pathlib import Path

from scripts.run_local_model_queue import render_table


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_context_filter_is_output_independent_and_preserves_original_indices():
    audit = load("artifacts/prompt_context_compatibility_173_v0_1.json")
    queue = load("artifacts/action_semantics_supported_queue_171_context_v0_1.json")
    excluded = {
        row["source_path"]
        for row in audit["records"]
        if not row["fits_requested_budget"]
    }
    assert excluded == {
        "packing_car_for_trip/problem0.bddl",
        "preparing_food_for_a_fundraiser/problem0.bddl",
    }
    assert audit["retained_count"] == queue["selected_count"] == 171
    assert queue["context_excluded"] == sorted(excluded)
    assert len({row["original_task_index"] for row in queue["records"]}) == 171
    assert all(
        audit["records"][row["original_task_index"]]["source_path"]
        == row["source_path"]
        for row in queue["records"]
    )


def test_projected_runs_are_complete_and_record_derivation():
    queue = load("artifacts/action_semantics_supported_queue_171_context_v0_1.json")
    expected = {row["source_path"] for row in queue["records"]}
    for slug in ("qwen3_4b", "phi4_mini", "mistral_7b"):
        report = load(
            f"artifacts/{slug}_queue_171_sampling_v0_9_context171_six.json"
        )
        assert report["summary"]["completed_task_count"] == 171
        assert report["summary"]["sample_count"] == 855
        assert {row["source_path"] for row in report["tasks"]} == expected
        assert report["derivation"]["regeneration"] is False
        assert report["derivation"]["type"] == (
            "model_output_independent_context_feasibility_projection"
        )


def test_result_table_title_uses_actual_task_count():
    assert render_table([]).splitlines()[0] == "# Frozen 0-task learned-baseline results"
