#!/usr/bin/env python3
"""Run a repeated-sampling local-model pilot and emit a result table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from planspace.bddl_parser import parse_problem_file
from planspace.core import action_ids, enumerate_valid_plans, execute_plan
from planspace.model_protocol import (
    MODEL_PROTOCOL_VERSION,
    parse_model_plan,
    prompt_sha256,
    render_model_prompt,
)
from planspace.pilot_domains import (
    ACTION_DOMAIN_VERSION,
    installing_a_printer_problem,
    moving_boxes_to_storage_problem,
    opening_doors_problem,
    organizing_file_cabinet_problem,
    storing_food_problem,
)


SPECS = {
    "installing_a_printer": (installing_a_printer_problem, 2, False),
    "opening_doors": (opening_doors_problem, 4, False),
    "moving_boxes_to_storage": (moving_boxes_to_storage_problem, 3, False),
    "organizing_file_cabinet": (organizing_file_cabinet_problem, 5, False),
    "storing_food": (storing_food_problem, 8, True),
}


def resolve_source(root: Path, activity: str) -> Path:
    for candidate in (
        root / activity / "problem0.bddl",
        root / f"{activity}_problem0.bddl",
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no problem0 source found for {activity}")


def render_table(rows: list[dict[str, object]]) -> str:
    lines = [
        "# Qwen3-8B five-task candidate pilot",
        "",
        "These are candidate-domain pilot measurements, not paper-level results.",
        "",
        "| Task | N | Parse | Executable | Goal valid | Exact | Unique valid | Space | Coverage |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {activity} | {sample_count} | {parse_success_rate:.1%} | "
            "{executable_rate:.1%} | {goal_valid_rate:.1%} | "
            "{exact_match_rate:.1%} | {unique_valid_plan_count} | "
            "{valid_plan_space_size} | {observed_plan_coverage:.1%} |".format(**row)
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
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
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        dtype=torch.bfloat16,
        device_map="cuda:0",
        local_files_only=True,
    )
    rows = []
    task_records = []
    for task_index, (activity, (adapter, max_depth, deduplicate)) in enumerate(
        SPECS.items()
    ):
        source = parse_problem_file(resolve_source(args.source_root, activity))
        problem = adapter(source)
        enumeration = enumerate_valid_plans(
            problem, max_depth=max_depth, deduplicate_states=deduplicate
        )
        valid_ids = {action_ids(plan) for plan in enumeration.plans}
        reference = action_ids(enumeration.plans[0])
        prompt = render_model_prompt(problem)
        messages = [
            {
                "role": "system",
                "content": "You are a symbolic embodied-task planner. Follow the output schema exactly.",
            },
            {"role": "user", "content": prompt},
        ]
        chat = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = tokenizer(chat, return_tensors="pt").to(model.device)
        samples = []
        for sample_index in range(args.samples):
            sample_seed = args.seed + task_index * 10_000 + sample_index
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
                        max_new_tokens=args.max_new_tokens,
                        pad_token_id=tokenizer.eos_token_id,
                    )
                generated_tokens = generated[0, inputs.input_ids.shape[1] :]
                generated_token_count = int(generated_tokens.shape[0])
                raw_output = tokenizer.decode(generated_tokens, skip_special_tokens=True)
                action_by_id = {action.action_id: action for action in problem.actions}
                parsed = parse_model_plan(raw_output, set(action_by_id))
                execution = execute_plan(
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
                    "enumerated_plan_member": parsed in valid_ids if parse_error is None else False,
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
        row = {
            "activity": activity,
            "sample_count": args.samples,
            "parse_success_rate": parsed_count / args.samples,
            "executable_rate": executable_count / args.samples,
            "goal_valid_rate": valid_count / args.samples,
            "exact_match_rate": exact_count / args.samples,
            "single_reference_false_rejection_among_valid": (
                (valid_count - exact_count) / valid_count if valid_count else None
            ),
            "unique_valid_plan_count": len(unique_valid),
            "valid_plan_space_size": len(valid_ids),
            "observed_plan_coverage": len(unique_valid & valid_ids) / len(valid_ids),
        }
        rows.append(row)
        task_records.append(
            {
                "activity": activity,
                "prompt_sha256": prompt_sha256(prompt),
                "input_tokens": int(inputs.input_ids.shape[1]),
                "reference_plan": list(reference),
                "metrics": row,
                "samples": samples,
            }
        )
        print(json.dumps(row), flush=True)

    total = args.samples * len(task_records)
    aggregate = {
        "sample_count": total,
        "parse_success_rate": sum(
            row["parse_success_rate"] * args.samples for row in rows
        )
        / total,
        "executable_rate": sum(row["executable_rate"] * args.samples for row in rows)
        / total,
        "goal_valid_rate": sum(row["goal_valid_rate"] * args.samples for row in rows)
        / total,
        "exact_match_rate": sum(row["exact_match_rate"] * args.samples for row in rows)
        / total,
    }
    total_valid = sum(
        row["goal_valid_rate"] * args.samples for row in rows
    )
    total_exact = sum(row["exact_match_rate"] * args.samples for row in rows)
    aggregate["single_reference_false_rejection_among_valid"] = (
        (total_valid - total_exact) / total_valid if total_valid else None
    )
    report = {
        "evidence_status": "candidate_five_task_repeated_sampling_not_paper_result",
        "protocol_version": MODEL_PROTOCOL_VERSION,
        "action_domain_version": ACTION_DOMAIN_VERSION,
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
        "aggregate_micro": aggregate,
        "table": rows,
        "tasks": task_records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.table_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.table_output.write_text(render_table(rows), encoding="utf-8")
    print(json.dumps(aggregate, indent=2))


if __name__ == "__main__":
    main()
