"""Deterministic structural screening for the PlanSpace compatibility audit."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from .bddl_parser import parse_problem_file, predicate_names
from .translation import goal_alternatives, initial_facts


DEFAULT_SUPPORTED_GOAL_PREDICATES = frozenset(
    {"inside", "ontop", "open", "toggled_on"}
)


def _stable_key(record: dict[str, Any], seed: str) -> tuple[str, str]:
    source_path = str(record["source_path"])
    digest = sha256(f"{seed}:{source_path}".encode("utf-8")).hexdigest()
    return digest, source_path


def structural_candidates(
    records: Iterable[dict[str, Any]],
    *,
    supported_goal_predicates: frozenset[str] = DEFAULT_SUPPORTED_GOAL_PREDICATES,
    max_object_count: int = 20,
) -> list[dict[str, Any]]:
    """Return records passing a deliberately syntax-only compatibility filter."""

    candidates = []
    for record in records:
        goal_predicates = frozenset(record["goal_predicates"])
        if not goal_predicates:
            continue
        if not goal_predicates <= supported_goal_predicates:
            continue
        if int(record["object_count"]) > max_object_count:
            continue
        candidates.append(record)
    return candidates


def select_stratified_records(
    records: Iterable[dict[str, Any]],
    *,
    target_count: int = 100,
    seed: str = "planspace-compatibility-v0.1",
    supported_goal_predicates: frozenset[str] = DEFAULT_SUPPORTED_GOAL_PREDICATES,
    max_object_count: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """Round-robin goal signatures so rare structural motifs remain represented."""

    if target_count <= 0:
        raise ValueError("target_count must be positive")
    candidates = structural_candidates(
        records,
        supported_goal_predicates=supported_goal_predicates,
        max_object_count=max_object_count,
    )
    if len(candidates) < target_count:
        raise ValueError(
            f"only {len(candidates)} records pass the structural filter; "
            f"cannot select {target_count}"
        )

    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in candidates:
        signature = tuple(sorted(record["goal_predicates"]))
        buckets[signature].append(record)
    for bucket in buckets.values():
        bucket.sort(key=lambda item: _stable_key(item, seed))

    signatures = sorted(buckets, key=lambda item: (len(buckets[item]), item))
    selected = []
    index = 0
    while len(selected) < target_count:
        added = False
        for signature in signatures:
            bucket = buckets[signature]
            if index < len(bucket):
                selected.append(bucket[index])
                added = True
                if len(selected) == target_count:
                    break
        if not added:
            raise RuntimeError("selection terminated before reaching target count")
        index += 1
    return selected, len(candidates)


def audit_selected_sources(
    activity_root: Path,
    selected_records: Iterable[dict[str, Any]],
    *,
    max_goal_alternatives: int = 10000,
) -> list[dict[str, Any]]:
    """Re-open selected raw sources and audit deterministic translation support.

    Passing this audit does not imply that an action domain exists or is faithful.
    """

    motif_by_fact_name = {
        "inside": "PLACE_IN_OR_TRANSFER",
        "ontop": "PLACE_ON_OR_TRANSFER",
        "open": "OPEN",
        "not_open": "CLOSE",
        "toggled_on": "TOGGLE_ON",
        "not_toggled_on": "TOGGLE_OFF",
    }
    audited = []
    for expected in selected_records:
        path = activity_root / expected["source_path"]
        base = {
            "problem_name": expected["problem_name"],
            "source_path": expected["source_path"],
            "source_sha256": sha256(path.read_bytes()).hexdigest() if path.exists() else None,
        }
        try:
            problem = parse_problem_file(path)
            observed_goal_predicates = sorted(predicate_names(problem.goal))
            source_consistent = (
                problem.problem_name == expected["problem_name"]
                and len(problem.objects) == expected["object_count"]
                and observed_goal_predicates == expected["goal_predicates"]
            )
            alternatives = goal_alternatives(
                problem, max_alternatives=max_goal_alternatives
            )
            goal_fact_names = sorted(
                {predicate.name for alternative in alternatives for predicate in alternative}
            )
            initial = initial_facts(problem)
            base.update(
                {
                    "translation_status": "pass" if source_consistent else "source_mismatch",
                    "source_record_consistent": source_consistent,
                    "initial_fact_count": len(initial),
                    "goal_alternative_count": len(alternatives),
                    "goal_fact_count_min": min(map(len, alternatives)),
                    "goal_fact_count_max": max(map(len, alternatives)),
                    "required_action_motifs": sorted(
                        {motif_by_fact_name[name] for name in goal_fact_names}
                    ),
                    "action_domain_status": "missing_or_unsigned",
                    "error": None,
                }
            )
        except Exception as error:
            base.update(
                {
                    "translation_status": "fail",
                    "source_record_consistent": False,
                    "initial_fact_count": None,
                    "goal_alternative_count": None,
                    "goal_fact_count_min": None,
                    "goal_fact_count_max": None,
                    "required_action_motifs": [],
                    "action_domain_status": "not_assessed",
                    "error": f"{type(error).__name__}: {error}",
                }
            )
        audited.append(base)
    return audited


def finalize_review_queue(
    screen: dict[str, Any],
    translation_audit: dict[str, Any],
    *,
    target_count: int = 100,
) -> dict[str, Any]:
    """Freeze the first translation-passing records in deterministic screen order."""

    audited_by_path = {
        record["source_path"]: record for record in translation_audit["records"]
    }
    passing = []
    for structural in screen["selected_records"]:
        audited = audited_by_path.get(structural["source_path"])
        if audited is None or audited["translation_status"] != "pass":
            continue
        passing.append({**structural, **audited})
    if len(passing) < target_count:
        raise ValueError(
            f"only {len(passing)} records passed translation; cannot freeze {target_count}"
        )
    selected = passing[:target_count]
    signature_counts: dict[str, int] = defaultdict(int)
    for record in selected:
        signature_counts["+".join(record["goal_predicates"])] += 1
    return {
        "evidence_status": "translation_compatible_pending_action_semantics_review",
        "queue_version": "planspace_action_semantics_review_v0.1",
        "source_screen_version": screen["screen_version"],
        "source_translation_audit_version": translation_audit["audit_version"],
        "available_translation_pass_count": len(passing),
        "selected_count": len(selected),
        "goal_signature_counts": dict(sorted(signature_counts.items())),
        "semantic_boundary": (
            "Every selected source parsed and its goal compiled within the declared bound. "
            "No record is benchmark-compatible until its action domain is implemented and "
            "independently reviewed."
        ),
        "records": selected,
    }
