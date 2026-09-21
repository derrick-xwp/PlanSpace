#!/usr/bin/env python3
"""Analyze two isolated output-validity audits against blinded metric labels."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


FIELDS = (
    "interface_compliant",
    "valid_at_declared_abstraction",
    "reasonable_high_level_behavior",
)


def kappa(left: list[str], right: list[str]) -> float | None:
    if not left:
        return None
    labels = sorted(set(left) | set(right))
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    lc, rc = Counter(left), Counter(right)
    expected = sum(lc[x] * rc[x] for x in labels) / (len(left) ** 2)
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def binary_report(predictions: list[bool], targets: list[bool]) -> dict:
    tp = sum(p and y for p, y in zip(predictions, targets))
    tn = sum((not p) and (not y) for p, y in zip(predictions, targets))
    fp = sum(p and (not y) for p, y in zip(predictions, targets))
    fn = sum((not p) and y for p, y in zip(predictions, targets))
    n = len(targets)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else 0.0
    return {
        "n": n,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": (tp + tn) / n if n else None,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def auroc(scores: list[float], targets: list[bool]) -> float | None:
    positive = [score for score, target in zip(scores, targets) if target]
    negative = [score for score, target in zip(scores, targets) if not target]
    if not positive or not negative:
        return None
    wins = 0.0
    for pos in positive:
        for neg in negative:
            wins += 1.0 if pos > neg else 0.5 if pos == neg else 0.0
    return wins / (len(positive) * len(negative))


def load_reviews(path: Path, expected_ids: list[str]) -> tuple[dict, dict[str, dict]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    reviews = report["reviews"]
    ids = [row["audit_id"] for row in reviews]
    if ids != expected_ids or len(set(ids)) != len(ids):
        raise ValueError(f"review IDs/order mismatch: {path}")
    return report, {row["audit_id"]: row for row in reviews}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("reviewer_a", type=Path)
    parser.add_argument("reviewer_b", type=Path)
    parser.add_argument("--adjudication", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--table-output", required=True, type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    ids = [row["audit_id"] for row in manifest["cases"]]
    left_report, left = load_reviews(args.reviewer_a, ids)
    right_report, right = load_reviews(args.reviewer_b, ids)

    agreement = {}
    for field in FIELDS:
        left_values = [left[x][field] for x in ids]
        right_values = [right[x][field] for x in ids]
        agreement[field] = {
            "agreement_count": sum(a == b for a, b in zip(left_values, right_values)),
            "agreement_rate": sum(a == b for a, b in zip(left_values, right_values)) / len(ids),
            "cohen_kappa": kappa(left_values, right_values),
            "reviewer_a_counts": dict(Counter(left_values)),
            "reviewer_b_counts": dict(Counter(right_values)),
        }

    manifest_by_id = {row["audit_id"]: row for row in manifest["cases"]}
    adjudicated = {}
    if args.adjudication:
        adjudication_report = json.loads(
            args.adjudication.read_text(encoding="utf-8")
        )
        decisions = adjudication_report["decisions"]
        expected_disagreement_ids = [
            audit_id
            for audit_id in ids
            if any(left[audit_id][field] != right[audit_id][field] for field in FIELDS)
        ]
        decision_ids = [row["audit_id"] for row in decisions]
        if decision_ids != expected_disagreement_ids or len(set(decision_ids)) != len(decision_ids):
            raise ValueError("adjudication IDs/order mismatch")
        adjudicated = {row["audit_id"]: row for row in decisions}

    consensus_rows = []
    for audit_id in ids:
        a = left[audit_id]["reasonable_high_level_behavior"]
        b = right[audit_id]["reasonable_high_level_behavior"]
        if a == b and a in {"yes", "no"}:
            consensus_rows.append((manifest_by_id[audit_id], a == "yes"))
        elif audit_id in adjudicated:
            decision = adjudicated[audit_id]["reasonable_high_level_behavior"]
            if decision in {"yes", "no"}:
                consensus_rows.append((manifest_by_id[audit_id], decision == "yes"))

    targets = [target for _, target in consensus_rows]
    metrics = {}
    for name in ("exact_match", "partial_order_match", "goal_valid"):
        metrics[name] = binary_report([bool(row[name]) for row, _ in consensus_rows], targets)
    similarity_scores = [float(row["ordered_action_similarity"]) for row, _ in consensus_rows]
    metrics["ordered_action_similarity"] = {
        "n": len(targets),
        "auroc": auroc(similarity_scores, targets),
    }

    result = {
        "evidence_status": "internal_ai_output_validity_audit_not_human_validation",
        "analysis_version": "planspace-output-validity-analysis-v0.1",
        "packet_version": manifest["packet_version"],
        "reviewer_a_role": left_report["reviewer_role"],
        "reviewer_b_role": right_report["reviewer_role"],
        "case_count": len(ids),
        "agreement": agreement,
        "consensus_reasonable_case_count": len(consensus_rows),
        "adjudication_case_count": len(adjudicated),
        "metric_validity_against_ai_consensus": metrics,
        "boundary": (
            "Labels come from agreement between two isolated Codex roles"
            + (" with a third isolated Codex role adjudicating disagreements" if adjudicated else "")
            + ". They quantify internal adversarial consistency and metric discrimination, "
            "not independent human or simulator construct validity."
        ),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Blinded output-level validity audit",
        "",
        result["boundary"],
        "",
        "## Reviewer agreement",
        "",
        "| Field | Agreement | Cohen's kappa |",
        "| --- | ---: | ---: |",
    ]
    for field, row in agreement.items():
        lines.append(
            f"| {field} | {row['agreement_count']}/{len(ids)} ({row['agreement_rate']:.1%}) | {row['cohen_kappa']:.3f} |"
        )
    lines.extend([
        "",
        "## Metric discrimination against consensus high-level reasonableness",
        "",
        "| Metric | N | Accuracy | Precision | Recall | F1 / AUROC |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for name in ("exact_match", "partial_order_match", "goal_valid"):
        row = metrics[name]
        lines.append(
            f"| {name} | {row['n']} | {row['accuracy']:.3f} | {row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} |"
        )
    sim = metrics["ordered_action_similarity"]
    lines.append(
        f"| ordered_action_similarity | {sim['n']} | -- | -- | -- | AUROC {sim['auroc']:.3f} |"
    )
    args.table_output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
