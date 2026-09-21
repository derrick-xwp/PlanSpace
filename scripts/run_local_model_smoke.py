#!/usr/bin/env python3
"""Run one reproducible local-model plan generation and validate it."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

from planspace.bddl_parser import parse_problem_file
from planspace.core import execute_plan
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


ADAPTERS = {
    "installing_a_printer": installing_a_printer_problem,
    "moving_boxes_to_storage": moving_boxes_to_storage_problem,
    "opening_doors": opening_doors_problem,
    "organizing_file_cabinet": organizing_file_cabinet_problem,
    "storing_food": storing_food_problem,
}


def resolve_source(root: Path, activity: str) -> Path:
    candidates = (
        root / activity / "problem0.bddl",
        root / f"{activity}_problem0.bddl",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no frozen problem0 source found for {activity}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("activity", choices=sorted(ADAPTERS))
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    source_path = resolve_source(args.source_root, args.activity)
    source = parse_problem_file(source_path)
    problem = ADAPTERS[args.activity](source)
    prompt = render_model_prompt(problem)
    messages = [
        {
            "role": "system",
            "content": "You are a symbolic embodied-task planner. Follow the output schema exactly.",
        },
        {"role": "user", "content": prompt},
    ]

    torch.manual_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        dtype=torch.bfloat16,
        device_map="cuda:0",
        local_files_only=True,
    )
    chat = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = tokenizer(chat, return_tensors="pt").to(model.device)
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=args.max_new_tokens,
            pad_token_id=tokenizer.eos_token_id,
        )
    elapsed = time.perf_counter() - started
    generated_tokens = generated[0, inputs.input_ids.shape[1] :]
    raw_output = tokenizer.decode(generated_tokens, skip_special_tokens=True)

    action_by_id = {action.action_id: action for action in problem.actions}
    parse_error = None
    execution = None
    plan_ids: tuple[str, ...] = tuple()
    try:
        plan_ids = parse_model_plan(raw_output, set(action_by_id))
        execution = execute_plan(problem, [action_by_id[item] for item in plan_ids])
    except (ValueError, json.JSONDecodeError) as error:
        parse_error = f"{type(error).__name__}: {error}"

    report = {
        "evidence_status": "model_smoke_test_not_paper_result",
        "protocol_version": MODEL_PROTOCOL_VERSION,
        "action_domain_version": ACTION_DOMAIN_VERSION,
        "activity": args.activity,
        "source_sha256": sha256(source_path.read_bytes()).hexdigest(),
        "model_id": args.model_id,
        "model_revision": args.model_revision,
        "seed": args.seed,
        "decoding": {"do_sample": False, "max_new_tokens": args.max_new_tokens},
        "prompt_sha256": prompt_sha256(prompt),
        "input_tokens": int(inputs.input_ids.shape[1]),
        "generated_tokens": int(generated_tokens.shape[0]),
        "elapsed_seconds": elapsed,
        "peak_gpu_memory_bytes": int(torch.cuda.max_memory_allocated()),
        "raw_output": raw_output,
        "parsed_plan": list(plan_ids),
        "parse_error": parse_error,
        "execution": None
        if execution is None
        else {
            "executable": execution.executable,
            "goal_satisfied": execution.goal_satisfied,
            "valid": execution.valid,
            "failure_step": execution.failure_step,
            "failed_action_id": execution.failed_action_id,
            "missing_preconditions": sorted(map(str, execution.missing_preconditions)),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "raw_output"}, indent=2))


if __name__ == "__main__":
    main()
