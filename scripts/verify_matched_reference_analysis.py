"""Check saved evidence using direct sequence/Counter comparisons."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", type=Path, required=True)
    args = ap.parse_args()
    out = args.analysis
    manifest = load(out / "manifest.json")
    for path, expected in manifest["inputs"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    for path, expected in manifest["outputs"].items():
        assert hashlib.sha256((out / path).read_bytes()).hexdigest() == expected, path
    refs = {t["task"]: t["references"] for t in load(ROOT / "artifacts/reviewer_revision_20260919/family_construction_v1.json")["tasks"]}
    summary = load(out / "summary.json")
    selections = load(out / "reference_selections.json")
    for corpus in ("natural", "search"):
        rows = load(out / (corpus + "_rows.json"))
        for row in rows:
            parsed = row.get("parsed", True)
            expected_exact = [i for i, r in enumerate(refs[row["task"]]) if parsed and row["plan"] == r["action_ids"]]
            expected_multiset = [i for i, r in enumerate(refs[row["task"]]) if parsed and Counter(row["plan"]) == Counter(r["action_ids"])]
            assert expected_exact == row["matches"]["exact"]
            assert expected_multiset == row["matches"]["multiset"]
        for k, task_selections in selections.items():
            sums = Counter()
            for row in rows:
                for chosen in task_selections[row["task"]]:
                    weight = 1 / len(task_selections[row["task"]])
                    for rule, indices in row["matches"].items():
                        if set(chosen).intersection(indices):
                            sums[rule + ("_tp" if row["valid"] else "_fp")] += weight
            for rule in ("exact", "family", "relaxed", "multiset"):
                measured = summary[corpus][k]["rules"][rule]
                assert abs(sums[rule + "_tp"] - measured["valid_accepted"]) < 1e-7
                assert abs(sums[rule + "_fp"] - measured["invalid_accepted"]) < 1e-7
    controls = load(out / "control_rows.json")
    assert len({(r["task"], tuple(r["plan"])) for r in controls}) == len(controls)
    for row in controls:
        assert Counter(row["plan"]) == Counter(row["reference"])
        assert row["plan"] != row["reference"]
        i = row["swapped_position"]
        altered = list(row["reference"])
        altered[i], altered[i+1] = altered[i+1], altered[i]
        assert altered == row["plan"]
    assert len(controls) == summary["controls"]["n"]
    print("PASS: input/output hashes, all matched Exact/multiset labels, all reference-budget counts, and control provenance.")


if __name__ == "__main__":
    main()
