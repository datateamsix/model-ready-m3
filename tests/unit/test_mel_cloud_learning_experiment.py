"""Cloud learning cycle: freeze revision, C-v1 control, declared-effect measurement."""

from __future__ import annotations

from app.mel.behavior import semantic_question_routing_effect
from app.mel.cloud_learning import (
    EXPECTED_V1_FINGERPRINT,
    EXPECTED_V1_VERSION,
    FROZEN_REVISION,
    assert_cv1_control,
    assert_domain_view_control,
    assert_frozen_runtime,
    measure_declared_effect,
)
from app.mel.models import MelError


def test_frozen_revision_rejects_other_runtime() -> None:
    try:
        assert_frozen_runtime({"revision": "modelready-m3-00012-8xq"})
        raise AssertionError("expected frozen-revision failure")
    except MelError as exc:
        assert FROZEN_REVISION in str(exc)


def test_domain_view_v1_control() -> None:
    assert_domain_view_control(
        {
            "domain_view_version": EXPECTED_V1_VERSION,
            "domain_view_fingerprint": EXPECTED_V1_FINGERPRINT,
            "promoted_lesson_count": 0,
        },
        version=EXPECTED_V1_VERSION,
        fingerprint=EXPECTED_V1_FINGERPRINT,
        promoted_lesson_count=0,
    )


def test_cv1_rejects_retrieved_claims_before_promotion() -> None:
    try:
        assert_cv1_control(
            {
                "action_ids": ["prem3-scenarios", "modeler-questions", "continue-eda"],
                "retrieved_claim_ids": ["DV-EXP-too-early"],
            }
        )
        raise AssertionError("expected C-v1 control failure")
    except MelError as exc:
        assert "retrieved experiential claims" in str(exc)


def test_declared_effect_measures_rank_change_without_inference() -> None:
    effect = semantic_question_routing_effect()
    before = {
        "action_ids": ["prem3-scenarios", "modeler-questions", "continue-eda"],
        "recommended_presentation_order": [
            "ASSESSMENT",
            "INSIGHT",
            "ADVISORY",
            "SEMANTIC_INTERVIEW",
            "MODELING_FEASIBILITY",
        ],
        "retrieved_claim_ids": [],
        "question_families": ["PROMOTION_TIMING"],
        "finding_ids": ["PREM3-SEMANTIC-OPEN"],
        "action_owners": ["PREM3", "MODELER", "PREM3"],
        "diagnostic_routes": [],
    }
    after = {
        **before,
        "action_ids": ["modeler-questions", "prem3-scenarios", "continue-eda"],
        "recommended_presentation_order": [
            "ASSESSMENT",
            "SEMANTIC_INTERVIEW",
            "INSIGHT",
            "ADVISORY",
            "MODELING_FEASIBILITY",
        ],
        "retrieved_claim_ids": ["DV-EXP-cand-semantic_question_routing-3ebf87fa174b"],
    }
    measured = measure_declared_effect(before, after, effect)
    assert measured["effect_succeeded"] is True
    assert measured["inference_used"] is False
    assert measured["undeclared_behavior_field_changes"] == []
    assert measured["delta"]["handoff_rank_before"] == 2
    assert measured["delta"]["handoff_rank_after"] == 1
