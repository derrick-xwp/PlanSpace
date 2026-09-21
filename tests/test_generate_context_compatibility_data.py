from paper.scripts.generate_context_compatibility_data import render


def test_context_audit_table_is_counted_and_output_independent():
    report = {
        "retained_count": 1,
        "excluded_count": 1,
        "context_limit": 4096,
        "requested_max_new_tokens": 512,
        "records": [
            {
                "source_path": "fits/problem0.bddl",
                "input_tokens": 100,
                "requested_max_new_tokens": 512,
                "fits_requested_budget": True,
            },
            {
                "source_path": "too_long/problem0.bddl",
                "input_tokens": 4000,
                "requested_max_new_tokens": 512,
                "fits_requested_budget": False,
            },
        ],
    }
    text = render(report)
    assert r"\newcommand{\ContextAuditRetainedCount}{1}" in text
    assert r"\newcommand{\ContextAuditExcludedCount}{1}" in text
    assert "model-output-independent" in text.lower()
    assert r"too\_long & 4,000 & 512 & 4,512" in text
