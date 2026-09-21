import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_simulation_packet_has_three_valid_contrasts():
    packet_path = ROOT / "artifacts" / "simulation_audit_task_packet_v0_3.json"
    if not packet_path.exists():
        return
    packet = json.loads(packet_path.read_text())
    assert packet["evidence_status"] == "frozen_before_simulator_outcomes"
    assert packet["expected_rollouts"] == 27
    assert packet["task_count"] == 3
    assert {task["stratum"] for task in packet["tasks"]} == {
        "goal_choice",
        "long_horizon",
        "operator_composition",
    }
    for task in packet["tasks"]:
        assert task["reference"]["goal_valid"] is True
        assert task["replay_valid_nonreference"]["goal_valid"] is True
        assert task["replay_valid_nonreference"]["exact_match"] is False
        assert task["required_action_deletion"]["valid"] is False
        evidence = task["replay_valid_nonreference"]["evidence"]
        if evidence["kind"] == "observed_model_output":
            assert evidence["model_id"] == packet["model_results"]["model_id"]
            assert evidence["model_revision"] == packet["model_results"]["model_revision"]
            assert evidence["model_results_sha256"] == packet["model_results"]["sha256"]
