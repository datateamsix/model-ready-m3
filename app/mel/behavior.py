"""Typed observable behavior effects and deterministic behavior fingerprints.

A score is not proof. Learning proof is a predeclared effect plus a
direct before/after comparison on behaviorally meaningful fields.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.mel.fingerprint import fingerprint_payload

SEMANTIC_HANDOFF_ACTION_ID = "modeler-questions"
DEFAULT_PRESENTATION_ORDER = (
    "ASSESSMENT",
    "INSIGHT",
    "ADVISORY",
    "SEMANTIC_INTERVIEW",
    "MODELING_FEASIBILITY",
)
SEMANTIC_FIRST_PRESENTATION_ORDER = (
    "ASSESSMENT",
    "SEMANTIC_INTERVIEW",
    "INSIGHT",
    "ADVISORY",
    "MODELING_FEASIBILITY",
)
DEFAULT_HANDOFF_ACTION_ORDER = (
    "prem3-scenarios",
    SEMANTIC_HANDOFF_ACTION_ID,
    "continue-eda",
)
SEMANTIC_FIRST_HANDOFF_ACTION_ORDER = (
    SEMANTIC_HANDOFF_ACTION_ID,
    "prem3-scenarios",
    "continue-eda",
)


class BehaviorEffectType(StrEnum):
    QUESTION_ROUTE_ADD = "QUESTION_ROUTE_ADD"
    QUESTION_PRIORITY_UP = "QUESTION_PRIORITY_UP"
    QUESTION_ROUTE_AVOID = "QUESTION_ROUTE_AVOID"
    FINDING_PRIORITY_UP = "FINDING_PRIORITY_UP"
    DIAGNOSTIC_ROUTE_CHANGE = "DIAGNOSTIC_ROUTE_CHANGE"
    HANDOFF_ACTION_ADD = "HANDOFF_ACTION_ADD"
    HANDOFF_PRIORITY_UP = "HANDOFF_PRIORITY_UP"
    SOURCE_GUIDANCE_ADD = "SOURCE_GUIDANCE_ADD"
    ROUTING_CALL_REDUCTION = "ROUTING_CALL_REDUCTION"
    PRESENTATION_ROUTE_CHANGE = "PRESENTATION_ROUTE_CHANGE"


class BehaviorDirection(StrEnum):
    LOWER_IS_BETTER = "LOWER_IS_BETTER"
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    MUST_EQUAL = "MUST_EQUAL"
    MUST_BECOME_TRUE = "MUST_BECOME_TRUE"
    MUST_BECOME_FALSE = "MUST_BECOME_FALSE"
    NON_DEGRADING = "NON_DEGRADING"


class ExpectedBehaviorEffect(BaseModel):
    """Predeclared observable effect. Must exist before holdout v2 execution."""

    type: BehaviorEffectType
    target: str
    condition: str
    baseline_measure: str
    success_measure: str
    direction: BehaviorDirection
    allowed_change_fields: list[str] = Field(default_factory=list)


def semantic_question_routing_effect() -> ExpectedBehaviorEffect:
    return ExpectedBehaviorEffect(
        type=BehaviorEffectType.HANDOFF_PRIORITY_UP,
        target=SEMANTIC_HANDOFF_ACTION_ID,
        condition=(
            "semantic readiness interview persisted and at least one open "
            "semantic question"
        ),
        baseline_measure="handoff_action_rank:modeler-questions",
        success_measure="rank <= 1",
        direction=BehaviorDirection.LOWER_IS_BETTER,
        allowed_change_fields=[
            "handoff_action_order",
            "recommended_presentation_order",
            "retrieved_claim_ids",
        ],
    )


def effect_as_text(effect: ExpectedBehaviorEffect) -> str:
    return (
        f"{effect.type.value} target={effect.target} "
        f"baseline={effect.baseline_measure} success={effect.success_measure} "
        f"direction={effect.direction.value}"
    )


def action_rank(action_ids: list[str], target: str) -> int | None:
    try:
        return action_ids.index(target) + 1
    except ValueError:
        return None


def presentation_rank(order: list[str], target: str) -> int | None:
    return action_rank(order, target)


def extract_behavior_snapshot(
    *,
    question_families: list[str],
    finding_ids: list[str],
    action_ids: list[str],
    action_owners: list[str],
    recommended_presentation_order: list[str],
    retrieved_claim_ids: list[str] | None = None,
    diagnostic_routes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "question_families": list(question_families),
        "finding_ids": list(finding_ids),
        "action_ids": list(action_ids),
        "action_owners": list(action_owners),
        "recommended_presentation_order": list(recommended_presentation_order),
        "retrieved_claim_ids": list(retrieved_claim_ids or []),
        "diagnostic_routes": list(diagnostic_routes or []),
    }


def behavior_fingerprint(snapshot: dict[str, Any]) -> str:
    return fingerprint_payload(snapshot)


def behavior_delta(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    effect: ExpectedBehaviorEffect,
) -> dict[str, Any]:
    before_actions = list(before.get("action_ids") or [])
    after_actions = list(after.get("action_ids") or [])
    before_present = list(before.get("recommended_presentation_order") or [])
    after_present = list(after.get("recommended_presentation_order") or [])
    return {
        "effect_type": effect.type.value,
        "target": effect.target,
        "question_rank_before": presentation_rank(before_present, "SEMANTIC_INTERVIEW"),
        "question_rank_after": presentation_rank(after_present, "SEMANTIC_INTERVIEW"),
        "handoff_rank_before": action_rank(before_actions, effect.target),
        "handoff_rank_after": action_rank(after_actions, effect.target),
        "actions_added": [item for item in after_actions if item not in before_actions],
        "actions_removed": [item for item in before_actions if item not in after_actions],
        "presentation_before": before_present,
        "presentation_after": after_present,
        "retrieved_claim_ids_before": list(before.get("retrieved_claim_ids") or []),
        "retrieved_claim_ids_after": list(after.get("retrieved_claim_ids") or []),
        "observed_change": before != after,
    }


def effect_succeeded(delta: dict[str, Any], effect: ExpectedBehaviorEffect) -> bool:
    if effect.type is BehaviorEffectType.HANDOFF_PRIORITY_UP:
        before = delta.get("handoff_rank_before")
        after = delta.get("handoff_rank_after")
        if before is None or after is None:
            return False
        if effect.direction is BehaviorDirection.LOWER_IS_BETTER:
            return int(after) <= 1 and int(after) < int(before)
        return False
    if effect.type is BehaviorEffectType.QUESTION_PRIORITY_UP:
        before = delta.get("question_rank_before")
        after = delta.get("question_rank_after")
        if before is None or after is None:
            return False
        return int(after) < int(before)
    if effect.type is BehaviorEffectType.PRESENTATION_ROUTE_CHANGE:
        return list(delta.get("presentation_before") or []) != list(
            delta.get("presentation_after") or []
        )
    if effect.type is BehaviorEffectType.HANDOFF_ACTION_ADD:
        return effect.target in (delta.get("actions_added") or [])
    if effect.type is BehaviorEffectType.QUESTION_ROUTE_ADD:
        return bool(delta.get("observed_change"))
    if effect.type is BehaviorEffectType.QUESTION_ROUTE_AVOID:
        return bool(delta.get("observed_change"))
    if effect.type is BehaviorEffectType.FINDING_PRIORITY_UP:
        return bool(delta.get("observed_change"))
    if effect.type is BehaviorEffectType.DIAGNOSTIC_ROUTE_CHANGE:
        return bool(delta.get("observed_change"))
    if effect.type is BehaviorEffectType.SOURCE_GUIDANCE_ADD:
        return bool(delta.get("observed_change"))
    if effect.type is BehaviorEffectType.ROUTING_CALL_REDUCTION:
        return bool(delta.get("observed_change"))
    raise AssertionError(f"unhandled behavior effect type: {effect.type}")
