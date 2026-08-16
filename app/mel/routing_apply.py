"""Apply retrieved ROUTING_HINT claims to presentation/handoff order.

Does not change MODEL_READY, official Meridian severity, or numeric
diagnostics. Retrieval is explicit and recorded.
"""

from __future__ import annotations

from typing import Any

from app.domain.intelligence.models import DomainView, DomainViewClaim, LearnedAuthority, SourceType
from app.mel.behavior import (
    DEFAULT_HANDOFF_ACTION_ORDER,
    DEFAULT_PRESENTATION_ORDER,
    SEMANTIC_FIRST_HANDOFF_ACTION_ORDER,
    SEMANTIC_FIRST_PRESENTATION_ORDER,
    SEMANTIC_HANDOFF_ACTION_ID,
    ExpectedBehaviorEffect,
)
from app.mel.models import LessonType

SEMANTIC_OPEN_CONDITIONS = (
    "semantic readiness interview persisted",
    "at least one open semantic question",
)


def observed_semantic_conditions(interview: dict[str, Any] | None) -> list[str]:
    payload = interview or {}
    questions = list(payload.get("questions") or [])
    open_questions = [
        item
        for item in questions
        if str(item.get("status") or "OPEN").upper() != "ANSWERED"
    ]
    observed: list[str] = []
    if questions or int(payload.get("question_count") or 0) > 0:
        observed.append("semantic readiness interview persisted")
    if open_questions or int(payload.get("question_count") or 0) > 0:
        observed.append("at least one open semantic question")
    return observed


def _normalize(values: list[str]) -> set[str]:
    return {item.strip().lower() for item in values if item and item.strip()}


def claim_matches(
    claim: DomainViewClaim,
    *,
    observed: set[str],
    fallback_conditions: list[str] | None = None,
) -> tuple[bool, list[str], list[str]]:
    needed_raw = list(claim.applicability_conditions or []) or list(
        fallback_conditions or []
    )
    needed = _normalize(needed_raw)
    if not needed:
        return False, [], needed_raw
    matched = sorted(needed & observed)
    unmatched = sorted(needed - observed)
    return needed.issubset(observed), matched, unmatched


def retrieve_routing_hints(
    view: DomainView,
    *,
    observed_conditions: list[str],
    fallback_conditions: list[str] | None = None,
) -> dict[str, Any]:
    observed = _normalize(observed_conditions)
    retrieved: list[DomainViewClaim] = []
    records: list[dict[str, Any]] = []
    for claim in view.active_claims():
        if claim.source_type is not SourceType.PROMOTED_EXPERIENCE:
            continue
        if claim.authority is not LearnedAuthority.ROUTING_HINT:
            continue
        matched, matched_conditions, unmatched_conditions = claim_matches(
            claim,
            observed=observed,
            fallback_conditions=fallback_conditions,
        )
        record = {
            "lesson_id": claim.source_version,
            "claim_id": claim.claim_id,
            "retrieved": True,
            "retrieval_reason": (
                f"{claim.claim_id} applicability matched {matched_conditions}"
                if matched
                else f"{claim.claim_id} applicability unmatched {unmatched_conditions}"
            ),
            "applicability_match": matched,
            "matched_conditions": matched_conditions,
            "unmatched_conditions": unmatched_conditions,
        }
        records.append(record)
        if matched:
            retrieved.append(claim)
    applicable = [item for item in records if item["applicability_match"]]
    reason = "; ".join(item["retrieval_reason"] for item in applicable) or (
        "no applicable promoted routing hint"
    )
    return {
        "retrieved_claims": retrieved,
        "records": records,
        "retrieved": bool(applicable),
        "applicability_match": bool(applicable),
        "retrieval_reason": reason,
        "retrieved_claim_ids": [claim.claim_id for claim in retrieved],
    }


def apply_routing_plan(
    view: DomainView,
    *,
    observed_conditions: list[str],
    fallback_conditions: list[str] | None = None,
    effect: ExpectedBehaviorEffect | None = None,
) -> dict[str, Any]:
    retrieval = retrieve_routing_hints(
        view,
        observed_conditions=observed_conditions,
        fallback_conditions=fallback_conditions or list(SEMANTIC_OPEN_CONDITIONS),
    )
    semantic_open = _normalize(list(SEMANTIC_OPEN_CONDITIONS)).issubset(
        _normalize(observed_conditions)
    )
    apply_semantic = retrieval["applicability_match"] and semantic_open
    presentation = list(
        SEMANTIC_FIRST_PRESENTATION_ORDER if apply_semantic else DEFAULT_PRESENTATION_ORDER
    )
    handoff = list(
        SEMANTIC_FIRST_HANDOFF_ACTION_ORDER if apply_semantic else DEFAULT_HANDOFF_ACTION_ORDER
    )
    return {
        **{key: value for key, value in retrieval.items() if key != "retrieved_claims"},
        "recommended_presentation_order": presentation,
        "handoff_action_order": handoff,
        "semantic_handoff_target": SEMANTIC_HANDOFF_ACTION_ID,
        "applied": apply_semantic,
        "effect": None if effect is None else effect.model_dump(mode="json"),
        "lesson_type": LessonType.SEMANTIC_QUESTION_ROUTING.value,
    }


def reorder_actions(actions: list[Any], action_order: list[str]) -> list[Any]:
    by_id: dict[str, Any] = {}
    for action in actions:
        action_id = getattr(action, "action_id", None)
        if action_id is None and isinstance(action, dict):
            action_id = action.get("action_id")
        if action_id:
            by_id[str(action_id)] = action
    ordered: list[Any] = []
    seen: set[str] = set()
    for action_id in action_order:
        if action_id in by_id:
            ordered.append(by_id[action_id])
            seen.add(action_id)
    for action in actions:
        action_id = getattr(action, "action_id", None)
        if action_id is None and isinstance(action, dict):
            action_id = action.get("action_id")
        key = str(action_id or "")
        if key and key not in seen:
            ordered.append(action)
            seen.add(key)
        elif not key:
            ordered.append(action)
    return ordered
