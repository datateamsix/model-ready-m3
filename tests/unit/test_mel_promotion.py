"""DOMAIN_VIEW promotion, idempotency, and EXPERIENCE_APPLIED tests."""

from __future__ import annotations

from pathlib import Path

from app.domain.intelligence.builder import load_current_domain_view
from app.mel.apply import record_application, retrieve_learned_claims
from app.mel.candidates import fixture_candidate
from app.mel.evaluate import evaluate_candidate
from app.mel.models import (
    EpisodeTerminalOutcome,
    EvaluationDecision,
    ExperienceEpisode,
    LearningReceiptEnum,
    RegressionResult,
)
from app.mel.promote import activate_promoted_view, load_active_view, stage_domain_view
from app.mel.regression import evaluate_routing_regression


def _episode() -> ExperienceEpisode:
    view = load_current_domain_view()
    assert view is not None
    return ExperienceEpisode(
        episode_id="ep-fixture",
        run_id="run-fixture",
        episode_started_at="2026-08-16T00:00:00+00:00",
        episode_closed_at="2026-08-16T01:00:00+00:00",
        terminal_outcome=EpisodeTerminalOutcome.MODEL_READY,
        domain_view_version=view.domain_view_version,
        domain_view_fingerprint=view.content_fingerprint,
        content_fingerprint="ep-fp",
    )


def _passing_regression() -> RegressionResult:
    return evaluate_routing_regression(
        matching_before={"routing": "parameter_first"},
        matching_after={"routing": "semantic_first"},
        nonmatching_before={"routing": "parameter_first"},
        nonmatching_after={"routing": "parameter_first"},
        model_ready_before="MODEL_READY",
        model_ready_after="MODEL_READY",
        meridian_origin_before="OFFICIAL_MERIDIAN_EDA",
        meridian_origin_after="OFFICIAL_MERIDIAN_EDA",
        numeric_before={"ratio": 3.74},
        numeric_after={"ratio": 3.74},
    )


def test_synthetic_promotion_emits_experience_learned(tmp_path: Path) -> None:
    view = load_current_domain_view()
    assert view is not None
    candidate = fixture_candidate()
    regression = _passing_regression()
    evaluation = evaluate_candidate(
        candidate, episodes=[_episode()], view=view, regression=regression
    )
    assert evaluation.decision is EvaluationDecision.PROMOTE
    staged = stage_domain_view(candidate, previous=view)
    assert staged.content_fingerprint != view.content_fingerprint
    assert staged.promoted_lesson_count == 1
    receipt = activate_promoted_view(
        candidate=candidate,
        evaluation=evaluation,
        staged=staged,
        previous=view,
        regression=regression,
        registry_dir=tmp_path,
    )
    assert receipt.receipt_type is LearningReceiptEnum.EXPERIENCE_LEARNED
    assert (tmp_path / "experience" / "promotion_receipt.json").is_file()
    active = load_active_view(tmp_path)
    assert active.domain_view_version != view.domain_view_version
    assert active.content_fingerprint == receipt.new_domain_view_fingerprint
    second = evaluate_candidate(
        candidate, episodes=[_episode()], view=active, regression=regression
    )
    assert second.decision is EvaluationDecision.REJECT
    assert second.novelty.value in {"DUPLICATE", "ALREADY_KNOWN", "NOT_EXPERIENTIAL_NOVELTY"}


def test_experience_applied_requires_retrieval_change_and_validation(
    tmp_path: Path,
) -> None:
    view = load_current_domain_view()
    assert view is not None
    candidate = fixture_candidate()
    regression = _passing_regression()
    evaluation = evaluate_candidate(
        candidate, episodes=[_episode()], view=view, regression=regression
    )
    staged = stage_domain_view(candidate, previous=view)
    receipt = activate_promoted_view(
        candidate=candidate,
        evaluation=evaluation,
        staged=staged,
        previous=view,
        regression=regression,
        registry_dir=tmp_path,
    )
    v2 = load_active_view(tmp_path)
    conditions = list(candidate.applicability_conditions)
    claims, reason = retrieve_learned_claims(
        v2, applicability_conditions=conditions, observed_conditions=conditions
    )
    assert claims
    applied = record_application(
        receipt=receipt,
        target_episode_id="ep-holdout",
        retrieved_claims=claims,
        retrieval_reason=reason,
        behavior_before={"routing": "parameter_first"},
        behavior_after={"routing": "semantic_first"},
        independent_validation_pass=True,
        regression_pass=True,
    )
    assert applied.receipt_type is LearningReceiptEnum.EXPERIENCE_APPLIED
    assert applied.retrieved is True

    no_change = record_application(
        receipt=receipt,
        target_episode_id="ep-holdout-same",
        retrieved_claims=claims,
        retrieval_reason=reason,
        behavior_before={"routing": "parameter_first"},
        behavior_after={"routing": "parameter_first"},
        independent_validation_pass=True,
        regression_pass=True,
    )
    assert no_change.receipt_type is not LearningReceiptEnum.EXPERIENCE_APPLIED

    wrong = record_application(
        receipt=receipt,
        target_episode_id="ep-holdout-wrong",
        retrieved_claims=claims,
        retrieval_reason=reason,
        behavior_before={"routing": "parameter_first"},
        behavior_after={"routing": "semantic_first"},
        independent_validation_pass=False,
        regression_pass=True,
    )
    assert wrong.receipt_type is LearningReceiptEnum.APPLICATION_FAILED

    unmatched, unmatched_reason = retrieve_learned_claims(
        v2,
        applicability_conditions=conditions,
        observed_conditions=["unrelated condition"],
    )
    assert unmatched == []
    skipped = record_application(
        receipt=receipt,
        target_episode_id="ep-holdout-nomatch",
        retrieved_claims=unmatched,
        retrieval_reason=unmatched_reason,
        behavior_before={"routing": "parameter_first"},
        behavior_after={"routing": "parameter_first"},
        independent_validation_pass=True,
        regression_pass=True,
    )
    assert skipped.receipt_type is LearningReceiptEnum.NOT_APPLICABLE


def test_learning_does_not_alter_model_ready_gate() -> None:
    result = _passing_regression()
    assert result.model_ready_stable is True
    assert result.meridian_origin_stable is True
    assert result.numeric_diagnostics_stable is True
