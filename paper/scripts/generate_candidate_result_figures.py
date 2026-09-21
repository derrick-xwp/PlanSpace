#!/usr/bin/env python3
"""Generate ten evidence-backed candidate figures for PlanSpace.

Every plotted value is read from a frozen JSON artifact in ``artifacts/``.
The script writes publication PDFs/SVGs, review PNGs, a contact sheet, and a
manifest that records the source file and the intended finding for each figure.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts"
FIG_DIR = ROOT / "paper" / "figures" / "candidates"
OUT_DIR = ROOT / "output" / "figure_candidates"

NAVY = "#17365D"
BLUE = "#447BA8"
CYAN = "#3D9DB4"
TEAL = "#23877E"
CORAL = "#D66A5F"
GOLD = "#C8952E"
GRAY = "#66788A"
LIGHT_GRAY = "#D9E0E7"
PALE = "#F4F7FA"

MODEL_ORDER = [
    "Qwen/Qwen3-14B",
    "Qwen/Qwen3-4B",
    "Qwen/Qwen3-8B",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "microsoft/Phi-4-mini-instruct",
    "allenai/OLMo-2-1124-7B-Instruct",
]
SHORT = {
    "Qwen/Qwen3-14B": "Qwen3-14B",
    "Qwen/Qwen3-4B": "Qwen3-4B",
    "Qwen/Qwen3-8B": "Qwen3-8B",
    "mistralai/Mistral-7B-Instruct-v0.3": "Mistral-7B",
    "microsoft/Phi-4-mini-instruct": "Phi-4-mini",
    "allenai/OLMo-2-1124-7B-Instruct": "OLMo-2-7B",
}


def load(name: str):
    return json.loads((ART / name).read_text())


def pct(x: float) -> float:
    return 100.0 * x


def style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#9AA8B5",
            "axes.linewidth": 0.8,
            "grid.color": "#DDE4EA",
            "grid.linewidth": 0.7,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def new_fig(title: str, subtitle: str = "", figsize=(8.8, 5.0)):
    fig = plt.figure(figsize=figsize)
    fig.suptitle(title, x=0.07, y=0.965, ha="left", color=NAVY, fontsize=15, fontweight="bold")
    if subtitle:
        fig.text(0.07, 0.912, subtitle, ha="left", color="#4B5D70", fontsize=9.5)
    return fig


def finish(fig, stem: str, source: str, *, bottom=0.14):
    fig.text(0.07, 0.035, f"Source: {source}", ha="left", color="#68798A", fontsize=7.4)
    fig.subplots_adjust(left=0.16, right=0.96, top=0.84, bottom=bottom)
    for ext in ("pdf", "svg", "png"):
        kwargs = {"bbox_inches": "tight", "facecolor": "white"}
        if ext == "png":
            kwargs["dpi"] = 220
        fig.savefig(FIG_DIR / f"{stem}.{ext}", **kwargs)
    plt.close(fig)


def annotate_bar(ax, bars, fmt="{:.0f}"):
    for bar in bars:
        value = bar.get_width()
        ax.text(value + 1.0, bar.get_y() + bar.get_height() / 2, fmt.format(value), va="center", fontsize=8)


def fig01_metric_separation(manifest):
    data = load("multi_model_comparison_v0_6.json")["aggregate"]
    y = np.arange(len(MODEL_ORDER))
    fig = new_fig(
        "Goal validity exceeds exact matching for five of six models",
        "The widest full-denominator gap is 19.8 percentage points; OLMo-2 is the only model with no observed gap.",
    )
    ax = fig.add_subplot(111)
    for i, model in enumerate(MODEL_ORDER):
        exact = pct(data[model]["exact"])
        family = pct(data[model]["partial_order"])
        goal = pct(data[model]["goal_valid"])
        ax.plot([exact, goal], [i, i], color=LIGHT_GRAY, lw=5, solid_capstyle="round", zorder=1)
        ax.scatter(exact, i, s=55, color=CORAL, label="Exact" if i == 0 else None, zorder=3)
        ax.scatter(family, i, s=55, color=BLUE, label="Partial-order family" if i == 0 else None, zorder=3)
        ax.scatter(goal, i, s=58, color=TEAL, label="Goal-valid" if i == 0 else None, zorder=3)
        gap = goal - exact
        ax.text(goal + 1.2, i, f"+{gap:.1f}", va="center", color=NAVY, fontsize=8.5, fontweight="bold")
    ax.set_yticks(y, [SHORT[m] for m in MODEL_ORDER])
    ax.invert_yaxis()
    ax.set_xlim(0, 102)
    ax.set_xlabel("Outputs accepted (%)")
    ax.grid(axis="x")
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.25), frameon=False)
    finish(fig, "candidate_01_metric_separation", "multi_model_comparison_v0_6.json; 3,000 outputs")
    manifest.append(("candidate_01_metric_separation", "Exact matching undercounts goal-valid plans for five of six models."))


def fig02_failure_stages(manifest):
    data = load("multi_model_comparison_v0_6.json")["aggregate"]
    labels = [SHORT[m] for m in MODEL_ORDER]
    categories = [
        ("Valid exact", TEAL),
        ("Valid non-exact", CYAN),
        ("Executable goal miss", GOLD),
        ("Failed action", CORAL),
        ("Parse failure", GRAY),
    ]
    values = {name: [] for name, _ in categories}
    for model in MODEL_ORDER:
        d = data[model]
        values["Valid exact"].append(pct(d["exact"]))
        values["Valid non-exact"].append(pct(d["goal_valid"] - d["exact"]))
        values["Executable goal miss"].append(pct(d["executable"] - d["goal_valid"]))
        values["Failed action"].append(pct(d["parse"] - d["executable"]))
        values["Parse failure"].append(pct(1.0 - d["parse"]))
    fig = new_fig(
        "Low scores arise from different failure stages",
        "Phi-4-mini and OLMo-2 lose most outputs at the interface; stronger Qwen models lose more through reference mismatch.",
    )
    ax = fig.add_subplot(111)
    left = np.zeros(len(labels))
    for name, color in categories:
        vals = np.asarray(values[name])
        ax.barh(np.arange(len(labels)), vals, left=left, color=color, label=name, height=0.64)
        left += vals
    ax.set_yticks(np.arange(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of all outputs (%)")
    ax.grid(axis="x")
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.28), frameon=False)
    finish(fig, "candidate_02_failure_stages", "multi_model_comparison_v0_6.json; categories derived from nested outcome rates")
    manifest.append(("candidate_02_failure_stages", "Models fail at different stages, separating interface errors from planning errors."))


def fig03_deterministic_controls(manifest):
    summary = load("deterministic_controls_100_v0_4.json")["summary"]
    fig = new_fig(
        "Exact match rejects every deliberately non-reference valid control",
        "Replay accepts all positive controls, while deletion controls fail the goal check on every task.",
        figsize=(8.8, 4.7),
    )
    ax1 = fig.add_subplot(121)
    names = ["Exact", "Partial-order", "Goal-valid"]
    vals = [pct(summary["positive_exact_match_rate"]), pct(summary["positive_partial_order_match_rate"]), pct(summary["positive_goal_valid_rate"])]
    bars = ax1.barh(names, vals, color=[CORAL, BLUE, TEAL], height=0.58)
    ax1.set_xlim(0, 108)
    ax1.set_xlabel("Positive controls accepted (%)")
    ax1.grid(axis="x")
    annotate_bar(ax1, bars)
    ax2 = fig.add_subplot(122)
    vals2 = [summary["deletion_goal_miss_count"], summary["deletion_precondition_failure_count"]]
    bars2 = ax2.barh(["Goal miss", "Failed action"], vals2, color=[GOLD, CORAL], height=0.58)
    ax2.set_xlim(0, 108)
    ax2.set_xlabel("Deletion controls (count)")
    ax2.grid(axis="x")
    annotate_bar(ax2, bars2)
    fig.subplots_adjust(left=0.10, right=0.96, top=0.80, bottom=0.23, wspace=0.46)
    fig.text(0.07, 0.035, "Source: deterministic_controls_100_v0_4.json; 100 positive and 100 deletion controls", fontsize=7.4, color="#68798A")
    for ext in ("pdf", "svg", "png"):
        kw = {"bbox_inches": "tight", "facecolor": "white"}
        if ext == "png": kw["dpi"] = 220
        fig.savefig(FIG_DIR / f"candidate_03_deterministic_controls.{ext}", **kw)
    plt.close(fig)
    manifest.append(("candidate_03_deterministic_controls", "Controlled alternatives isolate false rejection from genuine goal failure."))


def fig04_prefix_sensitivity(manifest):
    models = load("action_prefix_sensitivity_comparison_v0_6.json")["models"]
    by_model = {m["model_id"]: m for m in models}
    y = np.arange(len(MODEL_ORDER))
    fig = new_fig(
        "One removable prefix changes Phi-4-mini goal validity by 32.2 points",
        "The same normalization leaves the other five checkpoints unchanged.",
    )
    ax = fig.add_subplot(111)
    for i, model in enumerate(MODEL_ORDER):
        d = by_model[model]
        strict = pct(d["strict_goal_valid_rate"])
        norm = pct(d["normalized_goal_valid_rate"])
        ax.plot([strict, norm], [i, i], color=LIGHT_GRAY, lw=5, solid_capstyle="round")
        ax.scatter(strict, i, s=58, color=CORAL, label="Strict interface" if i == 0 else None, zorder=3)
        ax.scatter(norm, i, s=58, color=TEAL, label="Prefix-normalized" if i == 0 else None, zorder=3)
        if abs(norm - strict) > 0.1:
            ax.text(norm + 1.3, i, f"+{norm-strict:.1f}", va="center", color=NAVY, fontweight="bold", fontsize=9)
    ax.set_yticks(y, [SHORT[m] for m in MODEL_ORDER])
    ax.invert_yaxis()
    ax.set_xlim(0, 102)
    ax.set_xlabel("Goal-valid outputs (%)")
    ax.grid(axis="x")
    ax.legend(ncol=2, loc="lower center", bbox_to_anchor=(0.5, -0.24), frameon=False)
    finish(fig, "candidate_04_prefix_sensitivity", "action_prefix_sensitivity_comparison_v0_6.json; 3,000 outputs")
    manifest.append(("candidate_04_prefix_sensitivity", "A bounded interface normalization affects only Phi-4-mini and recovers 161 valid outputs."))


def fig05_prompt_effect(manifest):
    models = load("prompt_serialization_effect_v0_6.json")["models"]
    by_model = {m["model_id"]: m for m in models}
    y = np.arange(len(MODEL_ORDER))
    fig = new_fig(
        "Prompt serialization affects some checkpoints but not others",
        "Paired goal-validity change from the archived compact prompt to v0.6; bars show 95% task-bootstrap intervals.",
    )
    ax = fig.add_subplot(111)
    for i, model in enumerate(MODEL_ORDER):
        e = by_model[model]["effects"]["goal_valid"]
        est, lo, hi = pct(e["estimate"]), pct(e["ci95_low"]), pct(e["ci95_high"])
        color = CORAL if e["holm_reject_0_05"] else BLUE
        ax.errorbar(est, i, xerr=[[est-lo], [hi-est]], fmt="o", color=color, ecolor=color, capsize=4, ms=7)
        ax.text(hi + 0.8, i, f"{est:+.1f}", va="center", fontsize=8.5, color=NAVY)
    ax.axvline(0, color="#7F8C99", lw=1.2)
    ax.set_yticks(y, [SHORT[m] for m in MODEL_ORDER])
    ax.invert_yaxis()
    ax.set_xlim(-22, 13)
    ax.set_xlabel("Change in goal-valid rate (percentage points)")
    ax.grid(axis="x")
    ax.text(0.98, 0.02, "Coral: Holm-adjusted p < 0.05", transform=ax.transAxes, ha="right", fontsize=8, color="#4B5D70")
    finish(fig, "candidate_05_prompt_effect", "prompt_serialization_effect_v0_6.json; paired 100-task comparison")
    manifest.append(("candidate_05_prompt_effect", "Prompt serialization produces checkpoint-specific, not uniform, score shifts."))


def fig06_sampling_curve(manifest):
    models = load("sampling_curve_analysis_v0_6.json")["models"]
    by_model = {m["model_id"]: m for m in models}
    colors = [NAVY, BLUE, CYAN, TEAL, CORAL, GRAY]
    fig = new_fig(
        "Repeated sampling helps weaker checkpoints most",
        "Any-of-k goal validity rises from 10% to 28% for Phi-4-mini and 67% to 79% for Mistral-7B, but changes little for Qwen.",
    )
    ax = fig.add_subplot(111)
    for model, color in zip(MODEL_ORDER, colors):
        pts = by_model[model]["points"]
        xs = [p["k"] for p in pts]
        ys = [pct(p["metrics"]["any_goal_valid_rate"]["estimate"]) for p in pts]
        ax.plot(xs, ys, marker="o", lw=2.1, ms=5.5, color=color, label=SHORT[model])
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_ylim(0, 100)
    ax.set_xlabel("Samples per task (k)")
    ax.set_ylabel("Tasks with at least one goal-valid plan (%)")
    ax.grid(True)
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.28), frameon=False)
    finish(fig, "candidate_06_sampling_curve", "sampling_curve_analysis_v0_6.json; 100 tasks per checkpoint")
    manifest.append(("candidate_06_sampling_curve", "Additional samples mainly recover failures for weaker models; strong models plateau quickly."))


def fig07_structural_splits(manifest):
    strata = load("qwen3_8b_queue_100_analysis_v0_6.json")["strata"]["structural_split"]
    keys = ["iid_core", "ood_commutation", "ood_goal_choice", "ood_long_horizon", "ood_operator_composition"]
    labels = ["IID core", "Commutation", "Goal choice", "Long horizon", "Operator comp."]
    exact = [pct(strata[k]["exact_match_rate"]) for k in keys]
    family = [pct(strata[k]["partial_order_match_rate"]) for k in keys]
    goal = [pct(strata[k]["goal_valid_rate"]) for k in keys]
    x = np.arange(len(keys))
    w = 0.24
    fig = new_fig(
        "Goal-choice tasks expose the largest metric gap",
        "Qwen3-8B remains goal-valid on 86.3% of goal-choice outputs, while exact matching accepts 36.3%.",
    )
    ax = fig.add_subplot(111)
    ax.bar(x-w, exact, width=w, color=CORAL, label="Exact")
    ax.bar(x, family, width=w, color=BLUE, label="Partial-order family")
    ax.bar(x+w, goal, width=w, color=TEAL, label="Goal-valid")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 108)
    ax.set_ylabel("Outputs accepted (%)")
    ax.grid(axis="y")
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.25), frameon=False)
    ax.annotate("50.0-point gap", xy=(2+w, goal[2]), xytext=(2.55, 101), arrowprops=dict(arrowstyle="->", color=NAVY), color=NAVY, fontsize=8.5)
    finish(fig, "candidate_07_structural_splits", "qwen3_8b_queue_100_analysis_v0_6.json; 500 outputs")
    manifest.append(("candidate_07_structural_splits", "Goal-choice variation, rather than simple commutation, creates the largest reference bias."))


def fig08_length_effect(manifest):
    strata = load("qwen3_8b_queue_100_analysis_v0_6.json")["strata"]["length_stratum"]
    keys = ["1-3", "4-6", "7+"]
    x = np.arange(3)
    w = 0.24
    exact = [pct(strata[k]["exact_match_rate"]) for k in keys]
    family = [pct(strata[k]["partial_order_match_rate"]) for k in keys]
    goal = [pct(strata[k]["goal_valid_rate"]) for k in keys]
    fig = new_fig(
        "Long plans magnify reference bias without collapsing goal validity",
        "For 7+ action references, goal validity is 80.8% while exact matching is 44.0%.",
    )
    ax = fig.add_subplot(111)
    ax.bar(x-w, exact, width=w, color=CORAL, label="Exact")
    ax.bar(x, family, width=w, color=BLUE, label="Partial-order family")
    ax.bar(x+w, goal, width=w, color=TEAL, label="Goal-valid")
    ax.set_xticks(x, ["1-3 actions", "4-6 actions", "7+ actions"])
    ax.set_ylim(0, 105)
    ax.set_ylabel("Outputs accepted (%)")
    ax.grid(axis="y")
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.25), frameon=False)
    ax.text(2, 93, f"Gap: {goal[2]-exact[2]:.1f} points", ha="center", color=NAVY, fontweight="bold", fontsize=9)
    finish(fig, "candidate_08_length_effect", "qwen3_8b_queue_100_analysis_v0_6.json; Qwen3-8B, 500 outputs")
    manifest.append(("candidate_08_length_effect", "The single-reference penalty grows sharply with plan length."))


def fig09_replication(manifest):
    old = load("qwen3_8b_queue_100_analysis_v0_6.json")["strata"]["structural_split"]
    new = load("qwen3_8b_queue_173_analysis_v0_7_expanded.json")["strata"]["structural_split"]
    keys = ["iid_core", "ood_commutation", "ood_goal_choice", "ood_long_horizon", "ood_operator_composition"]
    labels = ["IID core", "Commutation", "Goal choice", "Long horizon", "Operator comp."]
    gap100 = [pct(old[k]["goal_valid_rate"] - old[k]["exact_match_rate"]) for k in keys]
    gap173 = [pct(new[k]["goal_valid_rate"] - new[k]["exact_match_rate"]) for k in keys]
    y = np.arange(len(keys))
    fig = new_fig(
        "The 173-task expansion preserves the structural pattern",
        "Goal-choice and long-horizon tasks retain the largest goal-valid minus exact-match gaps.",
    )
    ax = fig.add_subplot(111)
    ax.barh(y-0.18, gap100, height=0.34, color=BLUE, label="Frozen 100")
    ax.barh(y+0.18, gap173, height=0.34, color=TEAL, label="Expanded 173")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 55)
    ax.set_xlabel("Goal-valid minus exact match (percentage points)")
    ax.grid(axis="x")
    ax.legend(ncol=2, loc="lower center", bbox_to_anchor=(0.5, -0.24), frameon=False)
    finish(fig, "candidate_09_replication", "qwen3_8b_queue_100_analysis_v0_6.json and qwen3_8b_queue_173_analysis_v0_7_expanded.json")
    manifest.append(("candidate_09_replication", "The main structural finding replicates after expanding the supported task set."))


def fig10_metric_audit(manifest):
    audit = load("output_validity_ai_adjudicated_v0_1.json")
    metrics = audit["metric_validity_against_ai_consensus"]
    names = ["Exact", "Partial-order", "Goal-valid"]
    keys = ["exact_match", "partial_order_match", "goal_valid"]
    x = np.arange(3)
    w = 0.25
    acc = [pct(metrics[k]["accuracy"]) for k in keys]
    rec = [pct(metrics[k]["recall"]) for k in keys]
    f1 = [pct(metrics[k]["f1"]) for k in keys]
    fig = new_fig(
        "Replay aligns best with blinded high-level validity judgments",
        "Internal AI audit on 120 stratified outputs; labels are not independent human or simulator validation.",
        figsize=(8.8, 4.9),
    )
    ax = fig.add_subplot(121)
    ax.bar(x-w, acc, width=w, color=BLUE, label="Accuracy")
    ax.bar(x, rec, width=w, color=GOLD, label="Recall")
    ax.bar(x+w, f1, width=w, color=TEAL, label="F1")
    ax.set_xticks(x, names)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Score (%)")
    ax.grid(axis="y")
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.27), frameon=False)

    ax2 = fig.add_subplot(122)
    vals = [pct(metrics["ordered_action_similarity"]["auroc"]), pct(metrics["goal_valid"]["accuracy"])]
    bars = ax2.barh(["Ordered similarity\n(AUROC)", "Goal replay\n(accuracy)"], vals, color=[GRAY, TEAL], height=0.55)
    ax2.set_xlim(0, 105)
    ax2.set_xlabel("Score (%)")
    ax2.grid(axis="x")
    annotate_bar(ax2, bars, "{:.1f}")
    fig.subplots_adjust(left=0.09, right=0.96, top=0.80, bottom=0.20, wspace=0.42)
    fig.text(0.07, 0.035, "Source: output_validity_ai_adjudicated_v0_1.json; 120 stratified outputs", fontsize=7.4, color="#68798A")
    for ext in ("pdf", "svg", "png"):
        kw = {"bbox_inches": "tight", "facecolor": "white"}
        if ext == "png": kw["dpi"] = 220
        fig.savefig(FIG_DIR / f"candidate_10_metric_audit.{ext}", **kw)
    plt.close(fig)
    manifest.append(("candidate_10_metric_audit", "Goal replay has higher accuracy and recall than exact matching, partial-order membership, or ordered similarity on the internal audit."))


def write_manifest(manifest):
    lines = [
        "# PlanSpace candidate result figures",
        "",
        "All ten figures are generated from frozen experimental artifacts. No image in this set is presented as a robot rollout screenshot.",
        "",
    ]
    for index, (stem, finding) in enumerate(manifest, 1):
        lines += [f"## {index}. {stem}", "", f"Finding: {finding}", "", f"Files: `{stem}.pdf`, `{stem}.svg`, `{stem}.png`", ""]
    (OUT_DIR / "MANIFEST.md").write_text("\n".join(lines))


def make_gallery(manifest):
    with PdfPages(OUT_DIR / "PlanSpace_10_candidate_figures.pdf") as pdf:
        for stem, _ in manifest:
            img = Image.open(FIG_DIR / f"{stem}.png").convert("RGB")
            fig = plt.figure(figsize=(11.0, 7.2), facecolor="white")
            ax = fig.add_axes([0.025, 0.025, 0.95, 0.95])
            ax.imshow(img)
            ax.axis("off")
            pdf.savefig(fig, bbox_inches="tight", facecolor="white")
            plt.close(fig)

    thumbs = []
    for stem, _ in manifest:
        img = Image.open(FIG_DIR / f"{stem}.png").convert("RGB")
        img.thumbnail((850, 480))
        thumbs.append((stem, img.copy()))
    sheet = Image.new("RGB", (1800, 5 * 560), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    for idx, (stem, img) in enumerate(thumbs):
        row, col = divmod(idx, 2)
        x, y = 40 + col * 890, 35 + row * 560
        draw.text((x, y), f"{idx+1}. {stem.replace('candidate_', '').replace('_', ' ')}", fill=NAVY, font=font)
        sheet.paste(img, (x, y + 45))
    sheet.save(OUT_DIR / "PlanSpace_10_candidate_figures_contact_sheet.png")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    style()
    manifest = []
    fig01_metric_separation(manifest)
    fig02_failure_stages(manifest)
    fig03_deterministic_controls(manifest)
    fig04_prefix_sensitivity(manifest)
    fig05_prompt_effect(manifest)
    fig06_sampling_curve(manifest)
    fig07_structural_splits(manifest)
    fig08_length_effect(manifest)
    fig09_replication(manifest)
    fig10_metric_audit(manifest)
    write_manifest(manifest)
    make_gallery(manifest)
    print(f"Generated {len(manifest)} candidate figure groups in {FIG_DIR}")
    print(OUT_DIR / "PlanSpace_10_candidate_figures.pdf")


if __name__ == "__main__":
    main()
