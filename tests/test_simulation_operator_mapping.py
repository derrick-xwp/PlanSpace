import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_simulation_operator_mapping_is_frozen_and_complete():
    mapping = json.loads((ROOT / "configs" / "simulation_operator_mapping_v0_1.json").read_text())
    assert mapping["evidence_status"] == "frozen_before_first_simulator_rollout"
    assert set(mapping["operator_mappings"]) == {
        "transfer",
        "open",
        "close",
        "toggle_on",
        "toggle_off",
    }
    assert mapping["execution_budget"]["attempts_per_action"] == 1
    assert mapping["execution_budget"]["manual_intervention"] is False
    assert mapping["execution_budget"]["condition_specific_tuning"] is False
    assert mapping["evidence"]["preserve_failures"] is True
    assert "not BEHAVIOR-native" in mapping["claim_boundary"]
