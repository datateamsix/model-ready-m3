"""Typed behavior effects and fingerprints."""

from __future__ import annotations

from app.mel.behavior import (
    BehaviorEffectType,
    ExpectedBehaviorEffect,
    behavior_delta,
    behavior_fingerprint,
    effect_succeeded,
    extract_behavior_snapshot,
    semantic_question_routing_effect,
)


def test_behavior_fingerprint_ignores_identity_fields() -> None:
    left = extract_behavior_snapshot(
        question_families=["REMARKETING_TARGETING"],
        finding_ids=["PREM3-SEMANTIC-OPEN"],
        action_ids=["prem3-scenarios", "modeler-questions"],
        action_owners=["PREM3", "MODELER"],
        recommended_presentation_order=["ASSESSMENT", "ADVISORY"],
    )
    right = dict(left)
    assert behavior_fingerprint(left) == behavior_fingerprint(right)
    right["action_ids"] = ["modeler-questions", "prem3-scenarios"]
    assert behavior_fingerprint(left) != behavior_fingerprint(right)


def test_handoff_priority_effect_requires_lower_rank() -> None:
    effect = semantic_question_routing_effect()
    assert effect.type is BehaviorEffectType.HANDOFF_PRIORITY_UP
    before = extract_behavior_snapshot(
        question_families=["PROMOTION_TIMING"],
        finding_ids=["a"],
        action_ids=["prem3-scenarios", "modeler-questions", "continue-eda"],
        action_owners=["PREM3", "MODELER", "PREM3"],
        recommended_presentation_order=["ASSESSMENT", "ADVISORY", "SEMANTIC_INTERVIEW"],
    )
    after = extract_behavior_snapshot(
        question_families=["PROMOTION_TIMING"],
        finding_ids=["a"],
        action_ids=["modeler-questions", "prem3-scenarios", "continue-eda"],
        action_owners=["MODELER", "PREM3", "PREM3"],
        recommended_presentation_order=["ASSESSMENT", "SEMANTIC_INTERVIEW", "ADVISORY"],
        retrieved_claim_ids=["DV-EXP-1"],
    )
    delta = behavior_delta(before, after, effect=effect)
    assert effect_succeeded(delta, effect)
    unchanged = behavior_delta(before, before, effect=effect)
    assert not effect_succeeded(unchanged, effect)


def test_expected_behavior_effect_is_fully_specified() -> None:
    effect = ExpectedBehaviorEffect.model_validate(
        semantic_question_routing_effect().model_dump()
    )
    assert effect.target
    assert effect.baseline_measure
    assert effect.success_measure
    assert effect.condition
    assert effect.direction
