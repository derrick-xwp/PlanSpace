from paper.scripts.generate_prompt_effect_data import METRICS, ORDER, render


def _report():
    models = []
    for index, model_id in enumerate(ORDER):
        effects = {}
        for metric in METRICS:
            estimate = (index - 2) / 100
            effects[metric] = {
                "estimate": estimate,
                "ci95_low": estimate - 0.01,
                "ci95_high": estimate + 0.01,
                "holm_reject_0_05": index == 5,
            }
        models.append({"model_id": model_id, "effects": effects})
    return {
        "evidence_status": "controlled_same_seed_same_domain_prompt_serialization_comparison",
        "bootstrap": {"trials": 10_000},
        "models": models,
    }


def test_render_contains_all_models_and_significance_macros():
    text = render(_report())
    assert all(label in text for label in ("Qwen3-4B", "Qwen3-8B", "Mistral-7B", "Phi-4-mini"))
    assert r"\newcommand{\PromptEffectSignificantGoalCount}{1}" in text
    assert r"$^{\dagger}$" in text
    assert all(
        line.endswith(r" \\")
        for line in text.splitlines()
        if any(line.startswith(label + " &") for label in ("Qwen3-4B", "Qwen3-8B", "Qwen3-14B", "Mistral-7B", "OLMo-2-7B", "Phi-4-mini"))
    )
