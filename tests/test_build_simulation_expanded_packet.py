import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_expanded_packet_is_balanced_and_frozen():
    path = ROOT / "artifacts" / "simulation_audit_expanded_12_task_packet_v0_4.json"
    if not path.exists():
        return
    packet = json.loads(path.read_text())
    assert packet["evidence_status"] == "frozen_before_simulator_outcomes"
    assert packet["task_count"] == 12
    assert packet["expected_rollouts"] == 108
    assert Counter(task["stratum"] for task in packet["tasks"]) == {
        "goal_choice": 4,
        "long_horizon": 4,
        "operator_composition": 4,
    }
    pilot = json.loads((ROOT / "artifacts" / "simulation_audit_task_packet_v0_3.json").read_text())
    pilot_sources = {task["source_path"] for task in pilot["tasks"]}
    expanded_anchors = {task["source_path"] for task in packet["tasks"] if task["pilot_anchor"]}
    assert expanded_anchors == pilot_sources
    assert sum(task["pilot_anchor"] for task in packet["tasks"]) == 3
    for task in packet["tasks"]:
        assert task["reference"]["goal_valid"] is True
        assert task["replay_valid_nonreference"]["goal_valid"] is True
        assert task["replay_valid_nonreference"]["exact_match"] is False
        assert task["required_action_deletion"]["valid"] is False
