# PlanSpace reviewer artifact

PlanSpace evaluates predicted embodied plans at three distinct levels:

1. whether the output can be parsed into grounded actions;
2. whether replay under a declared symbolic action model reaches the goal; and
3. whether the plan matches one recorded sequence or a known partial-order family.

This repository is the public, read-only reviewer artifact for the paper. It
contains the evaluator, tests, frozen task records, all 5,130 outputs in the
primary six-model experiment, derived analyses, and the scripts that regenerate
paper-facing values. Model weights and BEHAVIOR-1K simulator assets are not
redistributed.

## Start here

The primary release is the shared-context-filtered matrix of 171 tasks, six
open-weight language models, and five samples per task. The exact model
revisions, prompt policy, generation settings, queue, and audit hashes are
recorded in
`configs/model_matrix_v0_9_context_171_six_model_gpuhub.json`. The historical
filename records where the run was executed; no cluster access is required to
verify the released outputs.

With [uv](https://docs.astral.sh/uv/) installed, run:

```bash
uv run --python 3.11 python scripts/verify_release_manifest.py
uv run --python 3.11 python -m scripts.verify_v09_context_release
uv run --python 3.11 --extra dev python -m pytest -q
```

The first command checks file integrity. The second checks the frozen matrix,
task count, shared prompts, model records, and context-filter audit. The final
command exercises the parser, translation layer, symbolic executor, action
abstraction, and model protocol.

Equivalent commands work in a Python 3.9+ virtual environment after installing
the package and `pytest`:

```bash
python -m pip install -e '.[dev]'
python scripts/verify_release_manifest.py
python -m scripts.verify_v09_context_release
python -m pytest -q
```

Expected result: the release verifier prints
`six-model 171-task v0.9 release verified`, and the focused test suite reports
the complete public test suite passing.

## Repository map

- `src/planspace/`: parser, symbolic transition model, evaluation, and
  partial-order machinery.
- `configs/`: frozen primary run configuration and public schemas.
- `artifacts/`: raw model outputs, scored records, controls, audits, and
  secondary analyses.
- `scripts/`: data processing, analysis, and verification entry points.
- `tests/`: unit and regression tests.
- `paper/`: generated LaTeX values and the data manifests used by the paper.
- `docs/CLAIM_EVIDENCE_LEDGER.md`: claim-to-artifact map and scope boundaries.
- `docs/DATASET_CARD.md`: intended use, provenance, and limitations.

## Reproducing a reported number

The most direct path is:

1. locate the claim in `docs/CLAIM_EVIDENCE_LEDGER.md`;
2. inspect its named JSON artifact under `artifacts/`;
3. run the corresponding generator under `paper/scripts/`; and
4. compare the output with the generated `.tex` files under `paper/`.

For example, the six-model comparison used by the metric-separation figure is
stored in `artifacts/multi_model_comparison_v0_9_context171_six.json`, while its
paper macros are in `paper/generated_v09_context.tex`.

## Evidence boundaries

Replay establishes validity only under the released high-level symbolic action
model. It does not establish grasp feasibility, collision-free motion,
navigation reachability, real-robot success, or deployment safety. The semantic
and output reviews included here are reproducible internal AI-assisted audits;
they are not independent human validation. The 171-task set is filtered for
action-model support and shared context fit, so it is not an unbiased estimate
over all BEHAVIOR-1K activities.

## Data and licensing

Code in this repository is released under the MIT License. Frozen records and
derived artifacts are supplied for paper verification. Upstream task
definitions, model checkpoints, and simulator assets remain governed by their
respective licenses; see `THIRD_PARTY.md`.
