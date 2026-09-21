# Canonical task-scope audit

This is a read-only P0 audit. No paper, macro, source packet, or historical result was modified.

## Recommendation

Use the 171-task v0.9 context-expanded matrix as the primary current scope. Retain the frozen 100-task v0.4/v0.5 benchmark as a historical subset with explicit labels. Do not merge denominators or silently rewrite 100-task claims as 171-task claims.

## Inconsistencies found

- `paper/main.tex` and `paper/candidate_result_figures.tex` contain 100-task claims for the earlier benchmark.
- `paper/generated_expanded_v09.tex` and the `*_queue_171_*_context171_six` artifacts use the 171-task expansion.
- `paper/README.md` describes both scopes but needs an explicit historical-subset versus primary-matrix boundary.

## Required review files

`paper/main.tex`, `paper/README.md`, `paper/candidate_result_figures.tex`, `paper/generated_expanded_v09.tex`, and `paper/scripts/generate_expanded_v09_data.py`.

## Automated checks

Validate task counts in every source artifact, verify table captions and generated macros against their source scope, check denominator arithmetic after regeneration, and fail on cross-scope citation.

See the JSON for exact locations and source artifacts.
