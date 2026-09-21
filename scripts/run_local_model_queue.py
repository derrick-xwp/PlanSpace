#!/usr/bin/env python3
"""Run a resumable learned baseline over the frozen 100-task queue."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from planspace.bddl_parser import parse_problem_file
from planspace.core import action_ids
from planspace.domain_registry import get_generic_domain
from planspace.model_protocol import (
    MODEL_PROTOCOL_VERSION,
    parse_model_plan,
    prompt_sha256,
    render_context_fit_model_prompt,
    render_model_prompt,
)


def summarize(tasks: list[dict[str, object]]) -> dict[str, object]:
    samples = [sample for task in tasks for sample in task["samples"]]
    total = len(samples)
    parsed = sum(sample["parse_error"] is None for sample in samples)
    executable = sum(
        bool(sample["execution"] and sample["execution"]["executable"])
        for sample in samples
    )
    valid = sum(
        bool(sample["execution"] and sample["execution"]["valid"])
        for sample in samples
    )
    exact = sum(bool(sample["exact_match"]) for sample in samples)
    return {
        "completed_task_count": len(tasks),
        "sample_count": total,
        "parse_success_rate": parsed / total if total else None,
        "executable_rate": executable / total if total else None,
        "goal_valid_rate": valid / total if total else None,
        "exact_match_rate": exact / total if total else None,
        "single_reference_false_rejection_among_valid": (
            (valid - exact) / valid if valid else None
        ),
        "generation_seconds_total": sum(sample["elapsed_seconds"] for sample in samples),
    }


def render_table(tasks: list[dict[str, object]]) -> str:
    lines = [
        f"# Frozen {len(tasks)}-task learned-baseline results",
        "",
        "Candidate action semantics pending independent review.",
        "",
        "| Task | N | Parse | Exec. | Goal | Exact | Unique valid | Input tok. |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for task in tasks:
        metrics = task["metrics"]
        lines.append(
            "| {activity} | {sample_count} | {parse_success_rate:.1%} | "
            "{executable_rate:.1%} | {goal_valid_rate:.1%} | "
            "{exact_match_rate:.1%} | {unique_valid_prediction_count} | "
            "{input_tokens} |".format(
                activity=task["activity"],
                input_tokens=task["input_tokens"],
                **metrics,
            )
        )
    summary = summarize(tasks)
    if tasks:
        lines.append(
            "| **Micro** | **{sample_count}** | **{parse_success_rate:.1%}** | "
            "**{executable_rate:.1%}** | **{goal_valid_rate:.1%}** | "
            "**{exact_match_rate:.1%}** | -- | -- |".format(**summary)
        )
    return "\n".join(lines) + "\n"


def write_checkpoint(
    output: Path,
    table_output: Path,
    metadata: dict[str, object],
    tasks: list[dict[str, object]],
) -> None:
    report = {**metadata, "summary": summarize(tasks), "tasks": tasks}
    output.parent.mkdir(parents=True, exist_ok=True)
    table_output.parent.mkdir(parents=True, exist_ok=True)
    payloads = (
        (output, json.dumps(report, indent=2) + "\n"),
        (table_output, render_table(tasks)),
    )
    for destination, payload in payloads:
        temporary = destination.with_name(f".{destination.name}.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--table-output", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument(
        "--prompt-template",
        choices=("canonical_full_catalog", "uniform_compact_action_catalog_v1"),
        default="canonical_full_catalog",
        help=(
            "Frozen input serialization. The uniform compact option is a "
            "separate, cross-model comparison track; it is never mixed with "
            "the canonical full-catalog track."
        ),
    )
    parser.add_argument(
        "--fit-context",
        action="store_true",
        help=(
            "Use a recorded compact action-catalog fallback for overlong "
            "prompts, then clamp generation length if necessary. The requested "
            "max-new-tokens remains in metadata; each task records its template "
            "and effective generation budget."
        ),
    )
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument(
        "--generic-domain-version",
        default="planspace_generic_household_v0.4-candidate",
        help=(
            "Frozen generic action-domain implementation. The default preserves "
            "the legacy direct-run behavior."
        ),
    )
    parser.add_argument(
        "--protocol-version",
        default=MODEL_PROTOCOL_VERSION,
        help="Recorded protocol identifier; v0.1 remains the compatibility default.",
    )
    parser.add_argument(
        "--evidence-status",
        default="candidate_100_task_model_run_pending_semantic_review",
    )
    args = parser.parse_args()

    domain = get_generic_domain(args.generic_domain_version)

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    metadata = {
        "evidence_status": args.evidence_status,
        "protocol_version": args.protocol_version,
        "generic_domain_version": domain.GENERIC_DOMAIN_VERSION,
        "queue_version": queue["queue_version"],
        "model_id": args.model_id,
        "model_revision": args.model_revision,
        "decoding": {
            "samples_per_task": args.samples,
            "seed_base": args.seed,
            "temperature": args.temperature,
            "top_p": args.top_p,
            "max_new_tokens": args.max_new_tokens,
            "enable_thinking": False,
        },
        "context_fit_policy": (
            "compact_action_catalog_then_clamp_generation"
            if args.fit_context
            else "strict"
        ),
        "prompt_template_policy": args.prompt_template,
    }
    tasks: list[dict[str, object]] = []
    if args.output.exists():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        identity = (
            "protocol_version",
            "generic_domain_version",
            "model_id",
            "model_revision",
            "decoding",
            "context_fit_policy",
            "prompt_template_policy",
        )
        if any(previous.get(key) != metadata.get(key) for key in identity):
            raise ValueError("existing checkpoint does not match requested frozen protocol")
        tasks = previous.get("tasks", [])
    completed = {task["source_path"] for task in tasks}

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_path,
        local_files_only=True,
        trust_remote_code=args.trust_remote_code,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        dtype=torch.bfloat16,
        device_map="cuda:0",
        local_files_only=True,
        trust_remote_code=args.trust_remote_code,
    )
    context_limit = int(getattr(model.config, "max_position_embeddings", 40960))

    for task_index, queued in enumerate(queue["records"]):
        if queued["source_path"] in completed:
            continue
        source = parse_problem_file(args.source_root / queued["source_path"])
        problem = domain.generic_household_problem(source)
        references = []
        for goal in problem.goal_alternatives:
            try:
                plan = domain.construct_goal_plan(problem, goal)
                if domain.execute_plan(problem, plan).valid:
                    references.append(plan)
            except Exception:
                pass
        if not references:
            raise RuntimeError(f"no validated reference for {queued['source_path']}")
        reference = action_ids(references[0])
        prompt_template = args.prompt_template
        prompt = (
            render_model_prompt(problem)
            if prompt_template == "canonical_full_catalog"
            else render_context_fit_model_prompt(problem)
        )

        def encode_chat(rendered_prompt: str):
            messages = [
                {
                    "role": "system",
                    "content": "You are a symbolic embodied-task planner. Follow the output schema exactly.",
                },
                {"role": "user", "content": rendered_prompt},
            ]
            chat = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            return chat, tokenizer(chat, return_tensors="pt").to(model.device)

        chat, inputs = encode_chat(prompt)
        if (
            inputs.input_ids.shape[1] + args.max_new_tokens > context_limit
            and args.fit_context
        ):
            # The canonical track may use a recorded fallback for an otherwise
            # impossible model-context run.  Uniform compact tracks never
            # enter this branch because they begin compact for every model.
            prompt_template = "context_fit_compact_action_catalog_v1"
            prompt = render_context_fit_model_prompt(problem)
            chat, inputs = encode_chat(prompt)
        effective_max_new_tokens = args.max_new_tokens
        if inputs.input_ids.shape[1] + effective_max_new_tokens > context_limit:
            if args.fit_context:
                effective_max_new_tokens = context_limit - int(inputs.input_ids.shape[1])
            if effective_max_new_tokens <= 0 or not args.fit_context:
                raise ValueError(
                    f"prompt exceeds context for {queued['source_path']}: "
                    f"{inputs.input_ids.shape[1]} + {args.max_new_tokens} > {context_limit}"
                )
        if effective_max_new_tokens != args.max_new_tokens:
            print(
                f"clamped max_new_tokens for {queued['source_path']}: "
                f"{args.max_new_tokens} -> {effective_max_new_tokens}",
                flush=True,
            )
        if inputs.input_ids.shape[1] + effective_max_new_tokens > context_limit:
            raise ValueError(
                f"prompt exceeds context for {queued['source_path']}: "
                f"{inputs.input_ids.shape[1]} + {effective_max_new_tokens} > {context_limit}"
            )
        action_by_id = {action.action_id: action for action in problem.actions}
        samples = []
        for sample_index in range(args.samples):
            seed_task_index = queued.get("original_task_index", task_index)
            sample_seed = args.seed + seed_task_index * 10_000 + sample_index
            torch.manual_seed(sample_seed)
            torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            raw_output = ""
            parsed = tuple()
            parse_error = None
            execution = None
            generated_token_count = 0
            try:
                with torch.inference_mode():
                    generated = model.generate(
                        **inputs,
                        do_sample=True,
                        temperature=args.temperature,
                        top_p=args.top_p,
                        max_new_tokens=effective_max_new_tokens,
                        pad_token_id=tokenizer.eos_token_id,
                    )
                generated_tokens = generated[0, inputs.input_ids.shape[1] :]
                generated_token_count = int(generated_tokens.shape[0])
                raw_output = tokenizer.decode(generated_tokens, skip_special_tokens=True)
                parsed = parse_model_plan(raw_output, set(action_by_id))
                execution = domain.execute_plan(
                    problem, [action_by_id[action_id] for action_id in parsed]
                )
            except Exception as error:
                parse_error = f"{type(error).__name__}: {error}"
            samples.append(
                {
                    "sample_index": sample_index,
                    "seed": sample_seed,
                    "generated_tokens": generated_token_count,
                    "elapsed_seconds": time.perf_counter() - started,
                    "peak_gpu_memory_bytes": int(torch.cuda.max_memory_allocated()),
                    "raw_output": raw_output,
                    "parsed_plan": list(parsed),
                    "parse_error": parse_error,
                    "exact_match": parsed == reference if parse_error is None else False,
                    "execution": None
                    if execution is None
                    else {
                        "executable": execution.executable,
                        "goal_satisfied": execution.goal_satisfied,
                        "valid": execution.valid,
                        "failure_step": execution.failure_step,
                        "failed_action_id": execution.failed_action_id,
                        "missing_preconditions": sorted(
                            map(str, execution.missing_preconditions)
                        ),
                    },
                }
            )
        parsed_count = sum(sample["parse_error"] is None for sample in samples)
        executable_count = sum(
            bool(sample["execution"] and sample["execution"]["executable"])
            for sample in samples
        )
        valid_count = sum(
            bool(sample["execution"] and sample["execution"]["valid"])
            for sample in samples
        )
        exact_count = sum(bool(sample["exact_match"]) for sample in samples)
        unique_valid = {
            tuple(sample["parsed_plan"])
            for sample in samples
            if sample["execution"] and sample["execution"]["valid"]
        }
        metrics = {
            "sample_count": args.samples,
            "parse_success_rate": parsed_count / args.samples,
            "executable_rate": executable_count / args.samples,
            "goal_valid_rate": valid_count / args.samples,
            "exact_match_rate": exact_count / args.samples,
            "unique_valid_prediction_count": len(unique_valid),
            "single_reference_false_rejection_among_valid": (
                (valid_count - exact_count) / valid_count if valid_count else None
            ),
        }
        tasks.append(
            {
                "activity": problem.problem_id,
                "source_path": queued["source_path"],
                "source_sha256": queued["source_sha256"],
                "prompt_sha256": prompt_sha256(prompt),
                "serialized_chat_sha256": prompt_sha256(chat),
                "prompt_template": prompt_template,
                "input_tokens": int(inputs.input_ids.shape[1]),
                "context_limit": context_limit,
                "effective_max_new_tokens": effective_max_new_tokens,
                "reference_plan": list(reference),
                "satisfiable_goal_alternative_count": len(references),
                "metrics": metrics,
                "samples": samples,
            }
        )
        write_checkpoint(args.output, args.table_output, metadata, tasks)
        print(
            f"{len(tasks)}/{len(queue['records'])} {queued['source_path']} "
            f"valid={valid_count}/{args.samples} exact={exact_count}/{args.samples}",
            flush=True,
        )

    write_checkpoint(args.output, args.table_output, metadata, tasks)
    print(json.dumps(summarize(tasks), indent=2))


if __name__ == "__main__":
    main()
