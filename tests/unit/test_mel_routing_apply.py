"""ROUTING_HINT application changes handoff order only when retrieved and applicable."""

from __future__ import annotations

from app.domain.intelligence.builder import load_current_domain_view
from app.domain.intelligence.models import LearnedAuthority
from app.mel.candidates import fixture_candidate
from app.mel.evaluate import evaluate_candidate
from app.mel.models import EpisodeTerminalOutcome, ExperienceEpisode, RegressionResult
from app.mel.promote import activate_promoted_view, load_active_view, stage_domain_view
from app.mel.routing_apply import (
    DEFAULT_HANDOFF_ACTION_ORDER,
    SEMANTIC_FIRST_HANDOFF_ACTION_ORDER,
    apply_routing_plan,
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


def test_v1_keeps_default_handoff_order() -> None:
    view = load_current_domain_view()
    assert view is not None
    plan = apply_routing_plan(
        view,
        observed_conditions=[
            "semantic readiness interview persisted",
            "at least one open semantic question",
        ],
    )
    assert plan["retrieved"] is False
    assert plan["handoff_action_order"] == list(DEFAULT_HANDOFF_ACTION_ORDER)


def test_promoted_routing_hint_reorders_matching_cases(tmp_path) -> None:
    view = load_current_domain_view()
    assert view is not None
    candidate = fixture_candidate(
        applicability_conditions=[
            "semantic readiness interview persisted",
            "at least one open semantic question",
        ],
        requested_authority=LearnedAuthority.ROUTING_HINT,
    )
    regression = RegressionResult(passed=True, detail="fixture")
    evaluation = evaluate_candidate(
        candidate, episodes=[_episode()], view=view, regression=regression
    )
    staged = stage_domain_view(candidate, previous=view)
    activate_promoted_view(
        candidate=candidate,
        evaluation=evaluation,
        staged=staged,
        previous=view,
        regression=regression,
        registry_dir=tmp_path,
    )
    v2 = load_active_view(tmp_path)
    matching = apply_routing_plan(
        v2,
        observed_conditions=list(candidate.applicability_conditions),
        fallback_conditions=list(candidate.applicability_conditions),
    )
    assert matching["retrieved"] is True
    assert matching["applicability_match"] is True
    assert matching["handoff_action_order"] == list(SEMANTIC_FIRST_HANDOFF_ACTION_ORDER)
    nonmatching = apply_routing_plan(
        v2,
        observed_conditions=[],
        fallback_conditions=list(candidate.applicability_conditions),
    )
    assert nonmatching["applicability_match"] is False
    assert nonmatching["handoff_action_order"] == list(DEFAULT_HANDOFF_ACTION_ORDER)
