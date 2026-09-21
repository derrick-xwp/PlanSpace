#!/usr/bin/env python3
"""Measure frozen prompt lengths before committing a uniform-context model run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from planspace.bddl_parser import parse_problem_file
from planspace.generic_domain import generic_household_problem
from planspace.model_protocol import render_context_fit_model_prompt, render_model_prompt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("model_path", type=Path)
    parser.add_argument("--template", choices=("canonical", "uniform_compact"), required=True)
    parser.add_argument("--max-new-tokens", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from transformers import AutoConfig, AutoTokenizer

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)
    config = AutoConfig.from_pretrained(args.model_path, local_files_only=True)
    context_limit = int(getattr(config, "max_position_embeddings", 40960))
    rows = []
    for record in queue["records"]:
        source = parse_problem_file(args.source_root / record["source_path"])
        problem = generic_household_problem(source)
        prompt = (
            render_model_prompt(problem)
            if args.template == "canonical"
            else render_context_fit_model_prompt(problem)
        )
        messages = [
            {
                "role": "system",
                "content": "You are a symbolic embodied-task planner. Follow the output schema exactly.",
            },
            {"role": "user", "content": prompt},
        ]
        chat = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        token_count = len(tokenizer(chat).input_ids)
        rows.append(
            {
                "source_path": record["source_path"],
                "input_tokens": token_count,
                "fits_requested_generation": token_count + args.max_new_tokens <= context_limit,
            }
        )
    counts = [row["input_tokens"] for row in rows]
    report = {
        "queue_version": queue["queue_version"],
        "model_path": str(args.model_path),
        "template": args.template,
        "requested_max_new_tokens": args.max_new_tokens,
        "context_limit": context_limit,
        "task_count": len(rows),
        "max_input_tokens": max(counts),
        "min_input_tokens": min(counts),
        "overflow_count": sum(not row["fits_requested_generation"] for row in rows),
        "tasks": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "tasks"}, indent=2))


if __name__ == "__main__":
    main()
