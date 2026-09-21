# PlanSpace evaluation suite

## Summary

PlanSpace is an execution-grounded evaluation suite for high-level embodied
plans. It reports interface compliance, exact reference agreement, membership
in known partial-order plan families, symbolic goal achievement, and normalized
cost separately.

The primary study contains 171 BEHAVIOR-derived tasks. A model-output-independent
filter first retains tasks supported by the declared action model and then
removes two prompts that do not fit the smallest evaluated model's 4,096-token
context window under the common 512-token output budget.

## Evaluation records

The frozen primary release contains 5,130 outputs: five samples from each of six
public, pinned language-model checkpoints on every retained task. It preserves
the task records, exact prompts, public checkpoint revisions, seeds, decoding
settings, raw generations, parsed plans, replay traces, metric outputs, and
analysis summaries.

The evaluated models are Qwen3-4B, Qwen3-8B, Qwen3-14B,
Mistral-7B-Instruct-v0.3, OLMo-2-1124-7B-Instruct, and
Phi-4-mini-instruct. Immutable revisions are listed in the primary run
configuration.

## Intended uses

- Compare reference matching with symbolic goal achievement.
- Diagnose parsing, precondition, execution, and terminal-goal failures.
- Study known partial-order families and repeated-sampling coverage.
- Reproduce the numerical claims in the accompanying paper.

## Out-of-scope uses

The suite does not establish grasp feasibility, collision-free motion,
navigation reachability, capacity constraints, real-robot success, safety, or
human preference. A symbolically valid transfer is not evidence that a physical
robot can execute the manipulation.

## Selection and validation boundaries

The 171 tasks are compatibility- and context-filtered, rather than an unbiased
sample of all BEHAVIOR-1K activities. Replay establishes consistency with the
released symbolic model, not the real-world completeness of that abstraction.
Included semantic and output reviews are internal AI-assisted audits and must
not be represented as independent human validation.

## Provenance and licensing

Each released task and model record stores source identifiers and hashes.
PlanSpace does not redistribute model weights or simulator assets. Users must
comply with the upstream licenses of BEHAVIOR-1K/BDDL and the evaluated model
checkpoints. Code is released under the repository's MIT License.

