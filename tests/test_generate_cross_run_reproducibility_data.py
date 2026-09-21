import pytest

from paper.scripts.generate_cross_run_reproducibility_data import MODEL_LABELS, render


def report():
    records = []
    for model_id in MODEL_LABELS:
        records.append(
            {
                "model_id": model_id,
                "overlap_task_count": 100,
                "overlap_sample_count": 500,
                "prompt_hash_match_task_count": 100,
                "serialized_chat_hash_match_task_count": 100,
                "seed_match_sample_count": 15,
                "raw_output_match_rate": 0.978,
                "metrics": {
                    metric: {"new_minus_old": drift}
                    for metric, drift in {
                        "parse": 0.002,
                        "executable": 0.002,
                        "goal_valid": 0.004,
                        "exact": -0.006,
                    }.items()
                },
            }
        )
    return {
        "evidence_status": "posthoc_cross_run_diagnostic",
        "overlap_task_count": 100,
        "models": records,
    }


def test_renders_bounded_posthoc_table():
    text = render(report())
    assert "Post-hoc overlap diagnostic" in text
    assert "not a same-seed confirmatory experiment" in text
    assert r"\newcommand{\CrossRunMinRawMatch}{97.8}" in text
    assert r"\newcommand{\CrossRunMaxAbsMetricDrift}{0.6}" in text
    assert "Qwen3-14B" in text


def test_rejects_prompt_drift():
    value = report()
    value["models"][0]["prompt_hash_match_task_count"] = 99
    with pytest.raises(ValueError, match="prompt hash drift"):
        render(value)


def test_renders_feasibility_filtered_99_task_overlap():
    value = report()
    value["overlap_task_count"] = 99
    for row in value["models"]:
        row["overlap_task_count"] = 99
        row["overlap_sample_count"] = 495
        row["prompt_hash_match_task_count"] = 99
        row["serialized_chat_hash_match_task_count"] = 99
    text = render(value)
    assert r"\newcommand{\CrossRunOverlapTaskCount}{99}" in text
    assert "99/99" in text
    assert "/495" in text
