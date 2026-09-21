"""Export the verified matched-reference results without new paper macros."""
from pathlib import Path
import argparse
import json
import hashlib

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", type=Path, required=True)
    ap.add_argument("--analysis", type=Path, default=ROOT / "artifacts/matched_reference_analysis_20260921")
    args = ap.parse_args()
    report = json.loads((args.analysis / "summary.json").read_text())
    paper = args.paper
    (paper / "data").mkdir(exist_ok=True)
    lines = ["x exact family relaxed multiset"]
    for i, k in enumerate(("1", "3", "5", "all"), 1):
        rules = report["natural"][k]["rules"]
        lines.append(str(i) + " " + " ".join(f'{rules[r]["valid_recall_pct"]:.8f}' for r in ("exact", "family", "relaxed", "multiset")))
    (paper / "data/matched_reference_coverage.dat").write_text("\n".join(lines) + "\n")
    names = {"Qwen/Qwen3-4B": "Qwen3-4B", "microsoft/Phi-4-mini-instruct": "Phi-4-mini",
             "mistralai/Mistral-7B-Instruct-v0.3": "Mistral-7B", "allenai/OLMo-2-1124-7B-Instruct": "OLMo-2-7B",
             "Qwen/Qwen3-8B": "Qwen3-8B", "Qwen/Qwen3-14B": "Qwen3-14B"}
    rows = []
    for model in names:
        r = report["models"][model]["all"]
        exact = int(r["rules"]["exact"]["valid_accepted"])
        family = int(r["rules"]["family"]["valid_accepted"])
        fp = int(r["rules"]["multiset"]["invalid_accepted"])
        rows.append(f'{names[model]} & {r["valid"]} & {exact} & {family} & {family-exact} & {fp} \\\\')
    r = report["natural"]["all"]
    rows += [r"\midrule", f'Pooled & {r["valid"]} & {int(r["rules"]["exact"]["valid_accepted"])} & {int(r["rules"]["family"]["valid_accepted"])} & {int(r["family_minus_exact"]["valid_count"])} & {int(r["rules"]["multiset"]["invalid_accepted"])} \\\\']
    table = [r"\begin{tabular}{lrrrrr}", r"\toprule",
             r"Model & Goal & Exact & Family & $\Delta$ & Multiset false accepts \\",
             r"\midrule"] + rows + [r"\bottomrule", r"\end{tabular}"]
    (paper / "generated_matched_reference_rows.tex").write_text("% Generated from summary.json; literal counts, no new macros.\n" + "\n".join(table) + "\n")
    (paper / "data/matched_reference_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    manifest = json.loads((args.analysis / "manifest.json").read_text())
    manifest["paper_exports"] = {
        name: hashlib.sha256((paper / name).read_bytes()).hexdigest()
        for name in ("generated_matched_reference_rows.tex", "data/matched_reference_coverage.dat", "data/matched_reference_summary.json")
    }
    (paper / "data/matched_reference_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Exported matched-reference paper data.")


if __name__ == "__main__":
    main()
