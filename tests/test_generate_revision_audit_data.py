import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_revision_audit_generator_uses_machine_readable_sources(tmp_path):
    independent = tmp_path / "independent.json"
    cap = tmp_path / "cap.json"
    cost = tmp_path / "cost.json"
    output = tmp_path / "generated.tex"
    manifest = tmp_path / "manifest.json"
    independent.write_text(json.dumps({"independence_boundary": "bounded", "summary": {
        "task_count": 171,
        "tasks_with_independent_solution": 160,
        "tasks_with_independent_nonreference_solution": 140,
        "independent_solution_count": 2000,
        "independent_nonreference_solution_count": 1800,
        "tasks_hitting_resource_bound": 30,
    }}))
    cap.write_text(json.dumps({"metric_boundary": "membership is direct", "summary": {
        "capped_representative_count": 12,
        "capped_task_count": 10,
        "unique_goal_plan_representative_count": 400,
        "tasks_with_observed_family_multiplicity": 120,
        "all_checked_orders_valid_at_every_cap": True,
        "maximum_exact_topological_order_count": 100000,
    }}))
    models = []
    for model_id in [
        "Qwen/Qwen3-4B", "microsoft/Phi-4-mini-instruct",
        "mistralai/Mistral-7B-Instruct-v0.3", "allenai/OLMo-2-1124-7B-Instruct",
        "Qwen/Qwen3-8B", "Qwen/Qwen3-14B",
    ]:
        models.append({
            "model_id": model_id, "goal_valid_count": 80, "output_count": 100,
            "thresholds": [
                {"normalized_cost_regret_threshold": threshold, "full_denominator_rate": 0.7}
                for threshold in [0.0, 0.25, 0.5, 1.0]
            ],
        })
    cost.write_text(json.dumps({"denominator_policy": "full denominator", "models": models}))
    subprocess.run([
        sys.executable, str(ROOT / "paper/scripts/generate_revision_audit_data.py"),
        str(independent), str(cap), str(cost), "--output", str(output),
        "--manifest-output", str(manifest),
    ], check=True)
    text = output.read_text()
    assert "\\IndependentSearchTaskCount}{171}" in text
    assert "\\CapSensitiveAllValid}{true}" in text
    assert "Qwen3-14B & 80.0 & 70.0" in text
    assert json.loads(manifest.read_text())["schema_version"] == "planspace.revision_audits_manifest.v0.1"
