"""Frozen text-to-plan protocol for learned baseline inference."""

from __future__ import annotations

from hashlib import sha256
import json

from .core import GroundAction, PlanningProblem


MODEL_PROTOCOL_VERSION = "planspace_text_plan_v0.1-candidate"


def _render_large_enumerated_goal(
    alternatives: tuple[frozenset, ...],
    common: frozenset,
    remainders: tuple[frozenset, ...],
) -> list[str]:
    lines = [
        f"Goal alternatives ({len(alternatives)}, exact compact enumerated form):",
        "Satisfy every common fact and all facts in any one listed alternative.",
    ]
    if common:
        lines.append("- Common: " + " AND ".join(map(str, sorted(common))))
    for index, remainder in enumerate(remainders, 1):
        rendered = " AND ".join(map(str, sorted(remainder))) or "(no additional facts)"
        lines.append(f"- G{index}: {rendered}")
    return lines


def _render_goal_alternatives(problem: PlanningProblem) -> list[str]:
    alternatives = problem.goal_alternatives or (problem.goal,)
    if len(alternatives) <= 32:
        lines = [f"Goal alternatives ({len(alternatives)}):"]
        for index, goal in enumerate(alternatives, 1):
            rendered = " AND ".join(map(str, sorted(goal)))
            lines.append(f"- G{index}: {rendered}")
        return lines

    common = frozenset.intersection(*alternatives)
    remainders = tuple(alternative - common for alternative in alternatives)
    slot_sets = tuple(
        {(predicate.name, predicate.args[0]) for predicate in remainder}
        for remainder in remainders
    )
    if not slot_sets or any(slots != slot_sets[0] for slots in slot_sets):
        return _render_large_enumerated_goal(alternatives, common, remainders)
    slots = sorted(slot_sets[0])
    choices = {
        slot: sorted(
            {
                predicate
                for remainder in remainders
                for predicate in remainder
                if (predicate.name, predicate.args[0]) == slot
            }
        )
        for slot in slots
    }
    represented_count = 1
    for values in choices.values():
        represented_count *= len(values)
    observed = {
        tuple(next(p for p in remainder if (p.name, p.args[0]) == slot) for slot in slots)
        for remainder in remainders
    }
    if represented_count != len(alternatives) or len(observed) != len(alternatives):
        return _render_large_enumerated_goal(alternatives, common, remainders)

    lines = [
        f"Goal alternatives ({len(alternatives)}, exact compact Cartesian form):",
        "Satisfy every common fact and choose exactly one fact from each independent group.",
    ]
    if common:
        lines.append("- Common: " + " AND ".join(map(str, sorted(common))))
    for index, slot in enumerate(slots, 1):
        lines.append(
            f"- Choice group C{index}: " + " OR ".join(map(str, choices[slot]))
        )
    return lines


def render_model_prompt(problem: PlanningProblem) -> str:
    """Render one symbolic problem without exposing a reference plan."""

    lines = [
        "Produce one executable plan that satisfies any declared goal alternative.",
        "Use only action_id strings from the allowed action catalog.",
        'Return exactly one JSON object: {"plan": ["action_id", ...]}',
        "Do not include explanations, Markdown, or invented actions.",
        "",
        f"Problem: {problem.problem_id}",
        "Initial state:",
    ]
    lines.extend(f"- {predicate}" for predicate in sorted(problem.initial_state))
    lines.append("")
    lines.extend(_render_goal_alternatives(problem))
    lines.extend(["", "Allowed action catalog:"])
    for action in sorted(problem.actions, key=lambda item: item.action_id):
        lines.append("- " + render_action_catalog_entry(action))
    return "\n".join(lines) + "\n"


def render_context_fit_model_prompt(problem: PlanningProblem) -> str:
    """Render a deterministic compact fallback for a bounded context window.

    This is deliberately not the canonical protocol template: it preserves the
    full initial state and exact goal representation, while replacing verbose
    action contracts with the complete set of permitted action identifiers and
    their operators.  Callers must record when this fallback is used so results
    cannot be mistaken for canonical-template results.
    """

    lines = [
        "Produce one executable plan that satisfies any declared goal alternative.",
        "Use only action_id strings from the allowed action catalog.",
        'Return exactly one JSON object: {"plan": ["action_id", ...]}',
        "Do not include explanations, Markdown, or invented actions.",
        "",
        f"Problem: {problem.problem_id}",
        "Initial state:",
    ]
    lines.extend(f"- {predicate}" for predicate in sorted(problem.initial_state))
    lines.append("")
    lines.extend(_render_goal_alternatives(problem))
    lines.extend(["", "Allowed action catalog (context-fit compact form):"])
    for action in sorted(problem.actions, key=lambda item: item.action_id):
        lines.append(f"- action_id={action.action_id}; operator={action.operator}")
    return "\n".join(lines) + "\n"


def render_action_catalog_entry(action: GroundAction) -> str:
    """Render the exact catalog record shown to a model."""

    preconditions = ", ".join(map(str, sorted(action.preconditions))) or "none"
    add_effects = ", ".join(map(str, sorted(action.add_effects))) or "none"
    delete_effects = ", ".join(map(str, sorted(action.delete_effects))) or "none"
    constraints = ", ".join(action.constraints) or "none"
    access_sources = ", ".join(action.access_sources) or "none"
    access_targets = ", ".join(action.access_targets) or "none"
    return (
        f"action_id={action.action_id}; operator={action.operator}; "
        f"pre=[{preconditions}]; add=[{add_effects}]; del=[{delete_effects}]; "
        f"constraints=[{constraints}]; access_sources=[{access_sources}]; "
        f"access_targets=[{access_targets}]"
    )


def prompt_sha256(prompt: str) -> str:
    return sha256(prompt.encode("utf-8")).hexdigest()


def _parse_plan_items(text: str) -> tuple[str, ...]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("model output does not contain a JSON object")
    payload = json.loads(text[start : end + 1])
    if set(payload) != {"plan"} or not isinstance(payload["plan"], list):
        raise ValueError('expected exactly one "plan" list')
    plan = tuple(payload["plan"])
    if not all(isinstance(action_id, str) for action_id in plan):
        raise ValueError("every plan item must be an action_id string")
    return plan


def parse_model_plan(text: str, allowed_action_ids: set[str]) -> tuple[str, ...]:
    """Parse a strict JSON plan, tolerating surrounding model chatter."""

    plan = _parse_plan_items(text)
    unknown = sorted(set(plan) - allowed_action_ids)
    if unknown:
        raise ValueError("unknown action_id values: " + ", ".join(unknown))
    return plan


def parse_model_plan_action_prefix_sensitivity(
    text: str, allowed_action_ids: set[str]
) -> tuple[str, ...]:
    """Parse after removing only a literal ``action_id=`` item prefix.

    This deliberately bounded repair is for a separately reported interface
    sensitivity. It does not perform fuzzy matching or change action content.
    """

    plan = tuple(
        action_id[len("action_id=") :]
        if action_id.startswith("action_id=")
        else action_id
        for action_id in _parse_plan_items(text)
    )
    unknown = sorted(set(plan) - allowed_action_ids)
    if unknown:
        raise ValueError("unknown action_id values after prefix normalization: " + ", ".join(unknown))
    return plan


def parse_model_plan_catalog_projection_sensitivity(
    text: str, actions: tuple[GroundAction, ...]
) -> tuple[str, ...]:
    """Project an exact copied catalog record back to its action identifier.

    This deliberately post-hoc sensitivity accepts only an already valid action
    identifier, its literal ``action_id=`` form, or an exact catalog record
    rendered by :func:`render_action_catalog_entry`. It does not split list
    items, fuzzy-match text, or repair malformed JSON.
    """

    allowed = {action.action_id for action in actions}
    catalog = {render_action_catalog_entry(action): action.action_id for action in actions}
    projected = []
    for item in _parse_plan_items(text):
        if item in allowed:
            projected.append(item)
        elif item.startswith("action_id=") and item[len("action_id=") :] in allowed:
            projected.append(item[len("action_id=") :])
        elif item in catalog:
            projected.append(catalog[item])
        else:
            raise ValueError("unknown action_id value after catalog projection: " + item)
    return tuple(projected)
