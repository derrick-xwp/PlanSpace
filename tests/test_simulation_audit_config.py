import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_simulation_pilot_is_frozen_and_factorial():
    config = json.loads((ROOT / "configs" / "simulation_audit_v0_1.json").read_text())
    pilot = config["pilot"]
    assert len(pilot["strata"]) == 3
    assert all(len(stratum["ordered_candidates"]) >= 3 for stratum in pilot["strata"])
    assert pilot["conditions"] == [
        "reference",
        "replay_valid_nonreference",
        "required_action_deletion",
    ]
    assert pilot["seeds"] == [1001, 1002, 1003]
    assert pilot["expected_rollouts"] == 3 * 3 * 3


def test_smoke_acceptance_matches_protocol():
    config = json.loads((ROOT / "configs" / "simulation_audit_v0_1.json").read_text())
    smoke = config["acceptance"]["smoke"]
    assert smoke["minimum_lift_meters"] == 0.1
    assert smoke["maximum_terminal_position_error_meters"] == 0.05
    assert smoke["release_stability_seconds"] == 2.0
    assert smoke["maximum_stable_linear_speed_mps"] == 0.01
