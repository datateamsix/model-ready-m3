"""MEL candidate structure, novelty, and policy evaluation tests."""

from __future__ import annotations

import pytest

from app.domain.intelligence.builder import load_current_domain_view
from app.domain.intelligence.models import ClaimScope, LearnedAuthority, ScopeLevel
from app.mel.candidates import fixture_candidate, validate_candidate_structure
from app.mel.evaluate import evaluate_candidate
from app.mel.models import (
    EpisodeTerminalOutcome,
    EvaluationDecision,
    ExperienceEpisode,
    MelError,
    NoveltyClass,
)


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


def test_malformed_candidate_rejected() -> None:
    candidate = fixture_candidate(statement=" ", applicability_conditions=[])
    with pytest.raises(MelError):
        validate_candidate_structure(candidate)
    view = load_current_domain_view()
    assert view is not None
    result = evaluate_candidate(candidate, episodes=[_episode()], view=view)
    assert result.decision is EvaluationDecision.REJECT


def test_candidate_requires_core_fields() -> None:
    candidate = fixture_candidate()
    validate_candidate_structure(candidate)
    assert candidate.expected_behavior_change
    assert candidate.applicability_conditions


def test_duplicate_domain_view_claim_is_rejected() -> None:
    view = load_current_domain_view()
    assert view is not None
    existing = next(claim.statement for claim in view.active_claims())
    candidate = fixture_candidate(statement=existing)
    result = evaluate_candidate(candidate, episodes=[_episode()], view=view)
    assert result.decision is EvaluationDecision.REJECT
    assert result.novelty in {
        NoveltyClass.DUPLICATE,
        NoveltyClass.ALREADY_KNOWN,
        NoveltyClass.NOT_EXPERIENTIAL_NOVELTY,
    }


def test_normative_and_policy_and_causal_and_final_model_rejected() -> None:
    view = load_current_domain_view()
    assert view is not None
    episode = _episode()
    policy = fixture_candidate(
        statement="Missing media rows should always be filled with zero.",
        requested_authority=LearnedAuthority.ROUTING_HINT,
    )
    causal = fixture_candidate(
        statement="GQV is always a mediator when upper-funnel media exists."
    )
    knots = fixture_candidate(statement="Use 130 knots in future final models.")
    negative = fixture_candidate(statement="Negative media is acceptable for provider X.")
    for candidate, expected in (
        (policy, "policy"),
        (causal, "causal"),
        (knots, "final-model"),
        (negative, "normative"),
    ):
        result = evaluate_candidate(candidate, episodes=[episode], view=view)
        assert result.decision is EvaluationDecision.REJECT, expected


def test_organization_leak_rejected() -> None:
    view = load_current_domain_view()
    assert view is not None
    candidate = fixture_candidate(
        statement="Music Center coordinates promotions with paid social.",
        scope=ClaimScope(level=ScopeLevel.ORGANIZATION, value="org-x"),
    )
    result = evaluate_candidate(candidate, episodes=[_episode()], view=view)
    assert result.decision is EvaluationDecision.REJECT


def test_privacy_marker_rejected() -> None:
    view = load_current_domain_view()
    assert view is not None
    candidate = fixture_candidate(
        statement="organization_id acme always uses Monday weeks."
    )
    result = evaluate_candidate(candidate, episodes=[_episode()], view=view)
    assert result.decision is EvaluationDecision.REJECT


def test_advisory_insufficient_evidence_is_held() -> None:
    view = load_current_domain_view()
    assert view is not None
    candidate = fixture_candidate(
        requested_authority=LearnedAuthority.ADVISORY,
        meridian_corroboration=True,
    )
    result = evaluate_candidate(candidate, episodes=[_episode()], view=view)
    assert result.decision is EvaluationDecision.HOLD_FOR_MORE_EVIDENCE


def test_auto_safe_policy_capped_in_first_cycle() -> None:
    view = load_current_domain_view()
    assert view is not None
    candidate = fixture_candidate(requested_authority=LearnedAuthority.AUTO_SAFE_POLICY)
    result = evaluate_candidate(candidate, episodes=[_episode()], view=view)
    assert result.decision is EvaluationDecision.GOVERNANCE_REQUIRED
