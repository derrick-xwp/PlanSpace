from paper.scripts.generate_expanded_coverage_data import MODEL_ID, SPLIT_LABELS, render


def test_expanded_table_is_data_driven_and_boundary_labeled():
    splits = {
        name: {
            "task_count": count,
            "goal_valid_rate": 0.8,
            "partial_order_match_rate": 0.7,
            "exact_match_rate": 0.6,
        }
        for name, count in zip(SPLIT_LABELS, (24, 89, 28, 25, 7))
    }
    comparison = {
        "aggregate": {MODEL_ID: {"goal_valid": 0.8, "partial_order": 0.7, "exact": 0.6}}
    }
    analysis = {"strata": {"structural_split": splits}}
    queue = {"selected_count": 173, "excluded_count": 2}

    text = render(comparison, analysis, queue)

    assert r"\newcommand{\ExpandedSupportedTaskCount}{173}" in text
    assert "compatibility-filtered" in text
    assert "Operator composition & 7" in text
    assert r"\newcommand{\ExpandedFigureExactCoordinates}" in text
    assert r"\newcommand{\ExpandedFigureGapSegments}" in text
    assert r"\newcommand{\ExpandedFigureGapAnnotations}" in text
    assert all(
        line.endswith(r" \\")
        for line in text.splitlines()
        if line.startswith(("Core &", "Commutation &", "Goal choice &", "Long horizon &", "Operator composition &", "Overall &"))
    )


def test_expanded_table_accepts_qwen_inside_six_model_comparison():
    splits = {
        name: {
            "task_count": count,
            "goal_valid_rate": 0.8,
            "partial_order_match_rate": 0.7,
            "exact_match_rate": 0.6,
        }
        for name, count in zip(SPLIT_LABELS, (24, 89, 28, 25, 7))
    }
    comparison = {
        "aggregate": {
            MODEL_ID: {"goal_valid": 0.8, "partial_order": 0.7, "exact": 0.6},
            "Qwen/Qwen3-4B": {"goal_valid": 0.7, "partial_order": 0.6, "exact": 0.5},
        }
    }
    text = render(
        comparison,
        {"strata": {"structural_split": splits}},
        {"selected_count": 173, "excluded_count": 2},
    )
    assert r"\newcommand{\ExpandedGoalValid}{80.0}" in text
