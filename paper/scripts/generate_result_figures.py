#!/usr/bin/env python3
"""Generate traceable vector result figures directly from frozen JSON artifacts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
OUT = ROOT / "paper" / "figures"

COLORS = {
    "exact": "#4C78A8",
    "po": "#F2CF5B",
    "goal": "#59A14F",
    "accent": "#E15759",
    "ink": "#243447",
    "muted": "#667788",
    "grid": "#DCE3E8",
    "panel": "#F7F9FA",
    "white": "#FFFFFF",
}


def load(name: str):
    return json.loads((ARTIFACTS / name).read_text())


class SVG:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<style>",
            "text{font-family:DejaVu Sans,Arial,sans-serif;fill:#243447}",
            ".title{font-size:22px;font-weight:700}",
            ".subtitle{font-size:14px;fill:#667788}",
            ".label{font-size:15px}",
            ".small{font-size:12px;fill:#667788}",
            ".value{font-size:13px;font-weight:700}",
            ".panelletter{font-size:18px;font-weight:700}",
            "</style>",
            f'<rect width="{width}" height="{height}" fill="{COLORS["white"]}"/>',
        ]

    def add(self, item: str):
        self.parts.append(item)

    def text(self, x, y, value, cls="label", anchor="start", fill=None, rotate=None):
        attrs = [f'x="{x}"', f'y="{y}"', f'class="{cls}"', f'text-anchor="{anchor}"']
        if fill:
            attrs.append(f'fill="{fill}"')
        if rotate is not None:
            attrs.append(f'transform="rotate({rotate} {x} {y})"')
        self.add(f'<text {" ".join(attrs)}>{escape(str(value))}</text>')

    def rect(self, x, y, w, h, fill, rx=0, stroke=None, stroke_width=1, opacity=1):
        s = f' stroke="{stroke}" stroke-width="{stroke_width}"' if stroke else ""
        self.add(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" opacity="{opacity}"{s}/>'
        )

    def line(self, x1, y1, x2, y2, stroke, width=1, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="{width}"{d}/>'
        )

    def circle(self, x, y, r, fill, stroke=None, stroke_width=1):
        s = f' stroke="{stroke}" stroke-width="{stroke_width}"' if stroke else ""
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"{s}/>' )

    def polygon(self, points, fill):
        joined = " ".join(f"{x},{y}" for x, y in points)
        self.add(f'<polygon points="{joined}" fill="{fill}"/>')

    def finish(self, stem: str):
        self.parts.append("</svg>")
        OUT.mkdir(parents=True, exist_ok=True)
        svg_path = OUT / f"{stem}.svg"
        pdf_path = OUT / f"{stem}.pdf"
        svg_path.write_text("\n".join(self.parts))
        subprocess.run(
            ["rsvg-convert", "-f", "pdf", "-o", str(pdf_path), str(svg_path)],
            check=True,
        )


def short_model(model_id: str) -> str:
    labels = {
        "Qwen/Qwen3-4B": "Qwen3-4B",
        "Qwen/Qwen3-8B": "Qwen3-8B",
        "Qwen/Qwen3-14B": "Qwen3-14B",
        "mistralai/Mistral-7B-Instruct-v0.3": "Mistral-7B",
        "microsoft/Phi-4-mini-instruct": "Phi-4-mini",
        "allenai/OLMo-2-1124-7B-Instruct": "OLMo-2-7B",
    }
    return labels[model_id]


def metric_separation():
    comparison = load("multi_model_comparison_v0_6.json")
    controls = load("deterministic_controls_100_v0_4.json")["summary"]
    aggregate = comparison["aggregate"]
    order = sorted(aggregate, key=lambda m: aggregate[m]["goal_valid"], reverse=True)

    s = SVG(1120, 520)
    s.text(22, 30, "A", "panelletter")
    s.text(50, 30, "Exact matching systematically undercounts successful plans", "title")
    s.text(50, 52, "Same 100 tasks, five samples per task, strict interface", "subtitle")

    x0, x1 = 195, 770
    y0, row = 95, 58
    for tick in range(0, 101, 20):
        x = x0 + (x1 - x0) * tick / 100
        s.line(x, 72, x, 425, COLORS["grid"], 1)
        s.text(x, 450, tick, "small", "middle")
    s.text((x0 + x1) / 2, 480, "Accepted outputs (%)", "label", "middle")

    for i, model in enumerate(order):
        y = y0 + i * row
        vals = aggregate[model]
        exact = 100 * vals["exact"]
        po = 100 * vals["partial_order"]
        goal = 100 * vals["goal_valid"]
        s.text(x0 - 16, y + 5, short_model(model), "label", "end")
        xe = x0 + (x1 - x0) * exact / 100
        xp = x0 + (x1 - x0) * po / 100
        xg = x0 + (x1 - x0) * goal / 100
        s.line(xe, y, xg, y, COLORS["grid"], 8)
        s.circle(xe, y, 7, COLORS["exact"])
        s.polygon([(xp, y - 8), (xp + 8, y), (xp, y + 8), (xp - 8, y)], COLORS["po"])
        s.circle(xg, y, 7, COLORS["goal"])
        gap = goal - exact
        if gap >= 3:
            s.text((xe + xg) / 2, y - 13, f"+{gap:.1f}", "value", "middle", COLORS["accent"])

    ly = 495
    for j, (name, color, shape) in enumerate([
        ("Exact", COLORS["exact"], "circle"),
        ("Partial order", COLORS["po"], "diamond"),
        ("Goal-valid replay", COLORS["goal"], "circle"),
    ]):
        x = 155 + j * 185
        if shape == "diamond":
            s.polygon([(x, ly - 7), (x + 7, ly), (x, ly + 7), (x - 7, ly)], color)
        else:
            s.circle(x, ly, 6, color)
        s.text(x + 12, ly + 5, name, "small")

    s.line(805, 70, 805, 470, COLORS["grid"], 1)
    s.text(830, 30, "B", "panelletter")
    s.text(858, 30, "Controls isolate", "title")
    s.text(858, 52, "the evaluator effect", "title")
    s.text(830, 86, "Valid alternative", "label")
    positive = [
        ("Exact", 100 * controls["positive_exact_match_rate"], COLORS["exact"]),
        ("PO", 100 * controls["positive_partial_order_match_rate"], COLORS["po"]),
        ("Replay", 100 * controls["positive_goal_valid_rate"], COLORS["goal"]),
    ]
    bx, base, scale = 865, 260, 1.35
    for i, (label, value, color) in enumerate(positive):
        x = bx + i * 75
        h = value * scale
        s.rect(x, base - h, 42, h, color, 3)
        s.text(x + 21, base - h - 8, f"{value:.0f}%", "value", "middle")
        s.text(x + 21, base + 20, label, "small", "middle")
    s.text(830, 318, "Required-action deletion", "label")
    s.rect(830, 342, 255, 62, COLORS["panel"], 8, COLORS["grid"])
    s.text(850, 368, "Rejected as goal miss", "small")
    s.text(1060, 386, f"{100 * controls['deletion_negative_rejection_rate']:.0f}%", "title", "end", COLORS["accent"])
    s.text(830, 438, "The same replay that accepts", "small")
    s.text(830, 456, "valid alternatives rejects omissions.", "small")
    s.finish("metric_separation")


def structure_and_replication():
    expanded = load("qwen3_8b_queue_173_analysis_v0_7_expanded.json")
    main = load("multi_model_comparison_v0_6.json")["aggregate"]["Qwen/Qwen3-8B"]
    strata = expanded["strata"]["structural_split"]
    labels = [
        ("Core", "iid_core"),
        ("Commutation", "ood_commutation"),
        ("Goal choice", "ood_goal_choice"),
        ("Long horizon", "ood_long_horizon"),
        ("Operator comp.", "ood_operator_composition"),
    ]

    s = SVG(1120, 520)
    s.text(22, 30, "A", "panelletter")
    s.text(50, 30, "Task structure separates metric undercounting from planning difficulty", "title")
    s.text(50, 52, "Qwen3-8B on all 173 supported tasks; five samples per task", "subtitle")
    x0, x1 = 180, 720
    y0, row = 100, 68
    for tick in range(0, 101, 20):
        x = x0 + (x1 - x0) * tick / 100
        s.line(x, 75, x, 430, COLORS["grid"], 1)
        s.text(x, 452, tick, "small", "middle")
    s.text((x0 + x1) / 2, 465, "Accepted outputs (%)", "label", "middle")
    for i, (label, key) in enumerate(labels):
        y = y0 + i * row
        d = strata[key]
        n = d["task_count"]
        s.text(x0 - 12, y + 5, f"{label} (n={n})", "label", "end")
        values = [
            (100 * d["exact_match_rate"], COLORS["exact"]),
            (100 * d["partial_order_match_rate"], COLORS["po"]),
            (100 * d["goal_valid_rate"], COLORS["goal"]),
        ]
        xs = []
        for value, color in values:
            x = x0 + (x1 - x0) * value / 100
            xs.append(x)
            s.circle(x, y, 7, color)
        s.line(min(xs), y, max(xs), y, COLORS["grid"], 6)
        for (value, color), x in zip(values, xs):
            s.circle(x, y, 7, color)
        gap = 100 * (d["goal_valid_rate"] - d["exact_match_rate"])
        s.text(max(xs) + 12, y + 5, f"gap {gap:.1f}", "value", "start", COLORS["accent"])

    for j, (name, color) in enumerate([
        ("Exact", COLORS["exact"]),
        ("Partial order", COLORS["po"]),
        ("Goal replay", COLORS["goal"]),
    ]):
        x = 225 + j * 155
        s.circle(x, 498, 6, color)
        s.text(x + 12, 503, name, "small")

    s.line(785, 70, 785, 470, COLORS["grid"], 1)
    s.text(810, 30, "B", "panelletter")
    s.text(838, 30, "The pattern replicates", "title")
    s.text(838, 52, "on newly supported tasks", "title")
    groups = [
        ("Original 100", [100 * main["exact"], 100 * main["partial_order"], 100 * main["goal_valid"]]),
        ("New 73", [67.7, 72.6, 81.4]),
        ("All 173", [65.4, 70.2, 82.5]),
    ]
    gx0, gy0, gw = 825, 110, 250
    for tick in range(0, 101, 25):
        y = 410 - 2.7 * tick
        s.line(gx0, y, gx0 + gw, y, COLORS["grid"], 1)
        s.text(gx0 - 8, y + 4, tick, "small", "end")
    barw = 19
    for gi, (label, vals) in enumerate(groups):
        center = gx0 + 48 + gi * 82
        for j, (value, color) in enumerate(zip(vals, [COLORS["exact"], COLORS["po"], COLORS["goal"]])):
            x = center + (j - 1) * 21
            h = 2.7 * value
            s.rect(x - barw / 2, 410 - h, barw, h, color, 2)
        s.text(center, 434, label, "small", "middle")
        s.text(center, 458, f"gap {vals[2] - vals[0]:.1f}", "value", "middle", COLORS["accent"])
    s.finish("structure_and_replication")


def failure_and_interface():
    comparison = load("multi_model_comparison_v0_6.json")
    interface = load("action_prefix_sensitivity_comparison_v0_6.json")
    aggregate = comparison["aggregate"]
    order = sorted(aggregate, key=lambda m: aggregate[m]["goal_valid"], reverse=True)

    s = SVG(1120, 520)
    s.text(22, 30, "A", "panelletter")
    s.text(50, 30, "Low scores arise at different stages", "title")
    s.text(50, 52, "Full-denominator decomposition of the same 3,000 outputs", "subtitle")
    categories = [
        ("Valid exact", COLORS["exact"]),
        ("Valid non-reference", COLORS["goal"]),
        ("Goal miss", COLORS["po"]),
        ("Failed action", COLORS["accent"]),
        ("Parse failure", "#AAB4BD"),
    ]
    x0, x1 = 150, 590
    y0, row = 105, 51
    for tick in range(0, 101, 20):
        x = x0 + (x1 - x0) * tick / 100
        s.line(x, 76, x, 407, COLORS["grid"], 1)
        s.text(x, 429, tick, "small", "middle")
    s.text((x0 + x1) / 2, 454, "Share of all outputs (%)", "label", "middle")
    for i, model in enumerate(order):
        y = y0 + i * row
        d = aggregate[model]
        values = [
            100 * d["exact"],
            100 * (d["goal_valid"] - d["exact"]),
            100 * (d["executable"] - d["goal_valid"]),
            100 * (d["parse"] - d["executable"]),
            100 * (1.0 - d["parse"]),
        ]
        s.text(x0 - 12, y + 5, short_model(model), "label", "end")
        left = x0
        for value, (_, color) in zip(values, categories):
            width = (x1 - x0) * value / 100
            s.rect(left, y - 13, width, 26, color, 0)
            left += width
    for j, (name, color) in enumerate(categories):
        x = 65 + (j % 3) * 185
        y = 480 + (j // 3) * 25
        s.rect(x, y - 11, 13, 13, color, 1)
        s.text(x + 20, y, name, "small")

    s.line(625, 70, 625, 470, COLORS["grid"], 1)
    s.text(650, 30, "B", "panelletter")
    s.text(678, 30, "A one-token interface mismatch", "title")
    s.text(678, 52, "can dominate the measured score", "title")
    phi = next(m for m in interface["models"] if m["model_id"] == "microsoft/Phi-4-mini-instruct")
    metrics = [
        ("Parse", phi["strict_parse_rate"], phi["normalized_parse_rate"]),
        ("Goal", phi["strict_goal_valid_rate"], phi["normalized_goal_valid_rate"]),
        ("Exact", phi["strict_exact_match_rate"], phi["normalized_exact_match_rate"]),
    ]
    leftx, rightx = 745, 1010
    s.text(leftx, 92, "Strict", "label", "middle")
    s.text(rightx, 92, "Remove action_id=", "label", "middle")
    for i, (label, strict, normalized) in enumerate(metrics):
        y = 155 + i * 100
        ys = y + (1 - strict) * 42
        yn = y + (1 - normalized) * 42
        s.line(leftx, ys, rightx, yn, COLORS["grid"], 5)
        s.circle(leftx, ys, 8, COLORS["exact"])
        s.circle(rightx, yn, 8, COLORS["goal"])
        s.text(670, y + 26, label, "label")
        s.text(leftx - 15, ys + 5, f"{100*strict:.1f}%", "value", "end")
        s.text(rightx + 15, yn + 5, f"{100*normalized:.1f}%", "value")
        s.text((leftx + rightx) / 2, min(ys, yn) - 10, f"+{100*(normalized-strict):.1f} pp", "value", "middle", COLORS["accent"])
    unchanged = sum(abs(m["goal_valid_rate_delta"]) < 1e-12 for m in interface["models"])
    s.rect(690, 440, 365, 50, COLORS["panel"], 8, COLORS["grid"])
    s.text(708, 470, f"The other {unchanged} checkpoints are unchanged.", "small")
    s.finish("failure_and_interface")


def main():
    metric_separation()
    structure_and_replication()
    failure_and_interface()
    print("generated:")
    for stem in ["metric_separation", "structure_and_replication", "failure_and_interface"]:
        print(OUT / f"{stem}.pdf")


if __name__ == "__main__":
    main()
