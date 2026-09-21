# Paper-facing generated evidence

This directory contains machine-generated LaTeX values, compact data manifests,
and the analysis scripts used to connect the frozen JSON artifacts to reported
paper results. It intentionally does not contain the submission manuscript or
conference style files; the repository is a reviewer code-and-data artifact,
not a second copy of the paper submission.

The current primary files are:

- `generated_v09_context.tex`: six-model scores, intervals, paired tests, and
  plotting coordinates for the 171-task matrix;
- `generated_expanded_v09.tex`: structural splits and the 71-task expansion;
- `generated_cross_run_v09.tex`: cross-run consistency checks;
- `generated_revision_audits.tex`: bounded search, family sensitivity, and
  cost checks;
- `generated_prompt_effect.tex`: the controlled prompt-serialization analysis;
- `data/revision_audits_manifest.json`: provenance for revision analyses; and
- `scripts/`: generators that read the root-level `artifacts/` directory.

Generated files are retained so a reviewer can inspect paper-facing numbers
without installing LaTeX. The source JSON artifacts remain authoritative.

