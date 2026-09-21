import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_authoritative_simulation_preregistration_is_consistent():
    path = ROOT / "artifacts" / "simulation_preregistration_v0_3.json"
    if not path.exists():
        return
    record = json.loads(path.read_text())
    assert record["evidence_status"] == "frozen_before_first_simulator_rollout"
    assert record["pilot_is_subset_of_expansion"] is True
    assert record["denominators"] == {
        "pilot_tasks": 3,
        "pilot_rollouts": 27,
        "expanded_tasks_total": 12,
        "expanded_rollouts_total": 108,
        "additional_rollouts_after_pilot": 81,
    }
    assert len(record["pilot_sources"]) == 3
    assert len(record["expanded_sources"]) == 12
    assert set(record["pilot_sources"]) <= set(record["expanded_sources"])
    assert record["operator_mapping_status"] == "frozen_before_first_simulator_rollout"
    assert "operator_mapping" in record["authoritative_sources"]
