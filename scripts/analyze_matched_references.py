"""Matched-reference ablation on frozen outputs, search probes, and swaps.

No model calls, new reference generation, or changes to the symbolic domain.
Run with PYTHONPATH=src python scripts/analyze_matched_references.py.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import time
from types import SimpleNamespace

import numpy as np

from planspace.bddl_parser import parse_problem_file
from planspace.core import execute_plan
from planspace.generic_domain import generic_household_problem
from planspace.partial_order import matches_partial_order

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "artifacts/reviewer_revision_20260919"
RULES = ("exact", "family", "relaxed", "multiset")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def signature(ids):
    return tuple(sorted(Counter(ids).items()))


def matched_indices(ids, parsed, refs):
    """Hold action occurrences fixed; never replace a multiset by a set."""
    scores = {r: [] for r in RULES}
    if not parsed:
        return scores
    for i, ref in enumerate(refs):
        if signature(ids) != signature(ref["action_ids"]):
            continue
        scores["multiset"].append(i)
        if list(ids) == ref["action_ids"]:
            scores["exact"].append(i)
        plan = [SimpleNamespace(action_id=a) for a in ref["action_ids"]]
        for rule, edge_key in (("family", "conservative_edges"), ("relaxed", "relaxed_edges")):
            if matches_partial_order(ids, plan, frozenset(map(tuple, ref[edge_key]))):
                scores[rule].append(i)
    assert set(scores["exact"]) <= set(scores["family"]) <= set(scores["relaxed"]) <= set(scores["multiset"])
    return scores


def select_references(n, seed, k):
    order = list(range(n))
    random.Random(seed).shuffle(order)
    return order if k == "all" else order[:min(k, n)]


def adjacent_swaps(ids):
    seen = {tuple(ids)}
    for i in range(len(ids) - 1):
        altered = list(ids)
        altered[i], altered[i + 1] = altered[i + 1], altered[i]
        if tuple(altered) not in seen:
            seen.add(tuple(altered))
            yield i, altered


def aggregate(rows, selections, trials, boot_seed):
    tasks = sorted({r["task"] for r in rows})
    ti = {t: i for i, t in enumerate(tasks)}
    # columns: n, valid, then TP and FP for each rule, historical exact.
    counts = np.zeros((len(tasks), 11), dtype=float)
    for row in rows:
        a = counts[ti[row["task"]]]
        a[0] += 1
        a[1] += row["valid"]
        a[10] += row["designated_exact"]
        choices = selections[row["task"]]
        for j, rule in enumerate(RULES):
            accepted = sum(bool(set(row["matches"][rule]) & set(s)) for s in choices) / len(choices)
            a[2 + 2*j + (not row["valid"])] += accepted
    total = counts.sum(axis=0)
    rng = np.random.default_rng(boot_seed)
    weights = rng.multinomial(len(tasks), np.full(len(tasks), 1 / len(tasks)), size=trials)
    boot = weights @ counts

    def interval(num, den):
        good = den > 0
        if not good.any():
            return None
        return [float(x) for x in np.percentile(100 * num[good] / den[good], [2.5, 97.5])]

    report = {"n": len(rows), "tasks": len(tasks), "valid": int(total[1]),
              "invalid": int(total[0] - total[1]), "rules": {}}
    for j, rule in enumerate(RULES):
        tp, fp = total[2+2*j:4+2*j]
        report["rules"][rule] = {
            "accepted": float(tp + fp), "valid_accepted": float(tp), "invalid_accepted": float(fp),
            "valid_recall_pct": float(100*tp/total[1]) if total[1] else None,
            "invalid_acceptance_pct": float(100*fp/(total[0]-total[1])) if total[0] > total[1] else None,
            "valid_recall_ci": interval(boot[:, 2+2*j], boot[:, 1]),
        }
    # Gain in valid acceptance, in percentage points over every output.
    gain = total[4] - total[2]
    report["family_minus_exact"] = {
        "valid_count": float(gain), "pp_all_outputs": float(100*gain/total[0]),
        "ci_pp_all_outputs": interval(boot[:, 4]-boot[:, 2], boot[:, 0]),
    }
    report["reference_count_gain_vs_designated"] = float(total[2]-total[10])
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/matched_reference_analysis_20260921")
    args = parser.parse_args()
    assert not args.output.exists(), "Use a new output directory; never overwrite an audit."
    started = time.monotonic()
    config_path = ROOT / "configs/matched_reference_analysis_v1.json"
    config = load(config_path)
    graph_path = ARCHIVE / "family_construction_v1.json"
    graph = load(graph_path)
    tasks = {t["task"]: t for t in graph["tasks"]}
    source_to_task = {t["source_path"]: t["task"] for t in graph["tasks"]}
    manifest = {str(config_path.relative_to(ROOT)): sha(config_path),
                str(graph_path.relative_to(ROOT)): sha(graph_path),
                str(Path(__file__).relative_to(ROOT)): sha(__file__)}
    for name in ("__init__.py", "core.py", "generic_domain.py", "bddl_parser.py", "partial_order.py", "translation.py"):
        p = ROOT / "src/planspace" / name
        manifest[str(p.relative_to(ROOT))] = sha(p)
    for name in ("fireplace_repair_verification.json", "family_sensitivity_v1.json"):
        p = ARCHIVE / name
        manifest[str(p.relative_to(ROOT))] = sha(p)

    problems, action_maps = {}, {}
    for name, task in tasks.items():
        p = ROOT / "tmp/automation_v05_authoritative_etWEL0/frozen_source" / task["source_path"]
        assert sha(p) == task["source_sha256"], name
        manifest[str(p.relative_to(ROOT))] = sha(p)
        problem = generic_household_problem(parse_problem_file(p))
        problems[name] = problem
        action_maps[name] = {a.action_id: a for a in problem.actions}
        for ref in task["references"]:
            assert execute_plan(problem, [action_maps[name][a] for a in ref["action_ids"]]).valid
    print("Validated all 171 source problems and 1403 archived representatives.", flush=True)

    def replay(name, ids, parsed=True):
        if not parsed:
            return False
        return execute_plan(problems[name], [action_maps[name][a] for a in ids]).valid

    corrected = load(ARCHIVE / "fireplace_repair_verification.json")
    old_rows = load(ARCHIVE / "family_sensitivity_v1.json")["rows"]
    old = {(r["model"], r["task"], r["sample_index"]): r for r in old_rows}
    natural, designated = [], {}
    for model in corrected["models"]:
        p = ROOT / model["corrected_artifact"]
        assert sha(p) == model["sha256"]
        manifest[str(p.relative_to(ROOT))] = sha(p)
        for task in load(p)["tasks"]:
            name = task["activity"]
            if name in designated:
                assert designated[name] == task["reference_plan"]
            designated[name] = task["reference_plan"]
            refs = tasks[name]["references"]
            assert designated[name] in [r["action_ids"] for r in refs]
            for sample in task["samples"]:
                parsed = sample["parse_error"] is None
                ids = sample["parsed_plan"] or []
                valid = replay(name, ids, parsed)
                assert valid == bool((sample.get("execution") or {}).get("valid"))
                matches = matched_indices(ids, parsed, refs)
                prev = old[(model["model"], name, sample["sample_index"])]
                assert matches["family"] == prev["conservative_indices"]
                assert matches["relaxed"] == prev["relaxed_indices"]
                assert bool(matches["multiset"]) == prev["multiset"]
                exact = parsed and ids == designated[name]
                assert exact == sample["exact_match"]
                natural.append({"task": name, "model": model["model"],
                                "sample_index": sample["sample_index"], "plan": ids,
                                "valid": valid, "parsed": parsed, "designated_exact": exact,
                                "matches": matches})
        print("Replayed and matched " + model["model"], flush=True)
    assert len(natural) == 5130

    probes_path = ARCHIVE / "independent_family_probes_v1.json"
    probes = load(probes_path)
    manifest[str(probes_path.relative_to(ROOT))] = sha(probes_path)
    search = []
    for row in probes["rows"]:
        name = source_to_task[row["task"]]
        assert replay(name, row["plan"])
        matches = matched_indices(row["plan"], True, tasks[name]["references"])
        assert bool(matches["family"]) == row["conservative"]
        search.append({"task": name, "plan": row["plan"], "valid": True,
                       "designated_exact": row["plan"] == designated[name],
                       "matches": matches, "example_index": row["archived_example_index"]})
    assert len(search) == 591

    controls = []
    for name, ids in designated.items():
        ref = next(r for r in tasks[name]["references"] if r["action_ids"] == ids)
        for position, altered in adjacent_swaps(ids):
            controls.append({"task": name, "plan": altered, "reference": ids,
                             "swapped_position": position, "valid": replay(name, altered),
                             "designated_exact": False,
                             "matches": matched_indices(altered, True, [ref])})
    print(f"Replayed {len(search)} search probes and {len(controls)} adjacent-swap controls.", flush=True)

    frozen_selections, results = {}, {"natural": {}, "search": {}, "models": {}}
    for k in config["reference_budgets"]:
        seeds = [7] if k == "all" else config["selection_seeds"]
        selections = {name: [select_references(len(t["references"]), s, k) for s in seeds]
                      for name, t in tasks.items()}
        frozen_selections[str(k)] = selections
        kwargs = dict(trials=config["bootstrap_trials"], boot_seed=config["bootstrap_seed"])
        for corpus, rows in (("natural", natural), ("search", search)):
            results[corpus][str(k)] = aggregate(rows, selections, **kwargs)
        for model in corrected["models"]:
            name = model["model"]
            results["models"].setdefault(name, {})[str(k)] = aggregate(
                [r for r in natural if r["model"] == name], selections, **kwargs)
        print("Summarized reference budget " + str(k), flush=True)

    results["controls"] = aggregate(controls, {n: [[0]] for n in tasks},
                                     config["bootstrap_trials"], config["bootstrap_seed"])
    results["controls"]["tasks_with_valid_swap"] = len({r["task"] for r in controls if r["valid"]})
    results["controls"]["tasks_with_invalid_swap"] = len({r["task"] for r in controls if not r["valid"]})
    results["controls"]["tasks_with_both"] = len(
        {r["task"] for r in controls if r["valid"]} & {r["task"] for r in controls if not r["valid"]})
    results["reference_counts"] = {
        "tasks": len(tasks), "representatives": sum(len(t["references"]) for t in tasks.values()),
        "tasks_at_least_3": sum(len(t["references"]) >= 3 for t in tasks.values()),
        "tasks_at_least_5": sum(len(t["references"]) >= 5 for t in tasks.values()),
        "mean_effective_k": {str(k): float(np.mean([min(k, len(t["references"])) for t in tasks.values()]))
                             for k in (1, 3, 5)},
        "archived_construction_relaxation_seconds": sum(t["seconds"] for t in tasks.values()),
    }
    results["existing_gap_decomposition"] = {
        "goal": sum(r["valid"] for r in natural),
        "designated_exact": sum(r["designated_exact"] for r in natural),
        "all_reference_exact": sum(bool(r["matches"]["exact"]) for r in natural),
        "all_reference_family": sum(bool(r["matches"]["family"]) for r in natural),
        "all_reference_relaxed": sum(bool(r["matches"]["relaxed"]) for r in natural),
    }
    # All three accepted sets are checked against replay, not assumed sound.
    results["sanity"] = {
        "family_invalid_natural": sum(bool(r["matches"]["family"]) and not r["valid"] for r in natural),
        "family_invalid_controls": sum(bool(r["matches"]["family"]) and not r["valid"] for r in controls),
        "references_all_replayed_valid": True,
        "archived_labels_reproduced": True,
    }
    args.output.mkdir(parents=True)
    for name, data in (("summary.json", results), ("natural_rows.json", natural),
                       ("search_rows.json", search), ("control_rows.json", controls),
                       ("reference_selections.json", frozen_selections)):
        (args.output / name).write_text(json.dumps(data, indent=2) + "\n")
    manifest_out = {"inputs": manifest, "config": config, "seconds": time.monotonic()-started,
                    "outputs": {p.name: sha(p) for p in args.output.glob("*.json")}}
    (args.output / "manifest.json").write_text(json.dumps(manifest_out, indent=2) + "\n")
    print(json.dumps({"decomposition": results["existing_gap_decomposition"],
                      "controls": results["controls"], "seconds": manifest_out["seconds"]}, indent=2))


if __name__ == "__main__":
    main()
