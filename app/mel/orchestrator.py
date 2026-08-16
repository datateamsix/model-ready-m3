"""Bounded MEL evaluation operation. Separate from MODEL_READY."""

from __future__ import annotations

from pathlib import Path

from app.core.run_repository import RunRepository
from app.domain.intelligence.models import DomainView
from app.mel.apply import record_application, retrieve_learned_claims
from app.mel.candidates import candidate_fingerprint, propose_candidates_from_reflection
from app.mel.episode import load_episode
from app.mel.evaluate import evaluate_candidate
from app.mel.holdout import reject_holdout_training
from app.mel.ledger import (
    record_candidate,
    record_evaluation,
    record_promotion,
    record_reflection,
)
from app.mel.models import (
    CandidateLesson,
    EvaluationDecision,
    ExperienceEpisode,
    LearningReceiptEnum,
    LessonEvaluation,
    MelError,
    PromotionReceipt,
    RegressionResult,
)
from app.mel.promote import activate_promoted_view, load_active_view, stage_domain_view
from app.mel.reflect import reflect_on_experience_episode


def evaluate_experience_episode(
    episode_id: str,
    *,
    repo: RunRepository,
    run_id: str,
    ledger_dir: Path,
    registry_dir: Path,
    regression_for: dict[str, RegressionResult] | None = None,
) -> dict[str, object]:
    episode = load_episode(repo, run_id)
    if episode is None or episode.episode_id != episode_id:
        raise MelError(f"closed episode not found: {episode_id}")
    reject_holdout_training(episode, action="candidate generation")
    reflection = reflect_on_experience_episode(episode_id, repo=repo, run_id=run_id)
    record_reflection(ledger_dir, reflection)
    view = load_active_view(registry_dir)
    seen: set[str] = set()
    evaluations: list[LessonEvaluation] = []
    promoted: PromotionReceipt | None = None
    candidates = propose_candidates_from_reflection(reflection, episode=episode)
    for candidate in candidates:
        digest = candidate.content_fingerprint or candidate_fingerprint(candidate)
        if digest in seen:
            continue
        seen.add(digest)
        record_candidate(ledger_dir, candidate)
        regression = (regression_for or {}).get(candidate.candidate_lesson_id)
        evaluation = evaluate_candidate(
            candidate, episodes=[episode], view=view, regression=regression
        )
        record_evaluation(ledger_dir, evaluation)
        evaluations.append(evaluation)
        if evaluation.decision is EvaluationDecision.PROMOTE and promoted is None:
            promoted = _promote(candidate, evaluation, view, registry_dir, regression)
            record_promotion(ledger_dir, promoted)
            view = load_active_view(registry_dir)
    return {
        "episode_id": episode.episode_id,
        "reflection_id": reflection.reflection_id,
        "candidate_count": len(candidates),
        "evaluations": [item.model_dump(mode="json") for item in evaluations],
        "promoted": None if promoted is None else promoted.model_dump(mode="json"),
        "decision_summary": [item.decision.value for item in evaluations],
        "experience_learned": promoted is not None,
        "status": (
            LearningReceiptEnum.EXPERIENCE_LEARNED.value
            if promoted is not None
            else LearningReceiptEnum.NO_SAFE_PROMOTABLE_LESSON.value
        ),
    }


def _promote(
    candidate: CandidateLesson,
    evaluation: LessonEvaluation,
    previous: DomainView,
    registry_dir: Path,
    regression: RegressionResult | None,
) -> PromotionReceipt:
    if regression is None or not regression.passed:
        raise MelError("promotion requires a passing regression result")
    staged = stage_domain_view(candidate, previous=previous)
    return activate_promoted_view(
        candidate=candidate,
        evaluation=evaluation,
        staged=staged,
        previous=previous,
        regression=regression,
        registry_dir=registry_dir,
    )


def apply_to_holdout(
    *,
    receipt: PromotionReceipt,
    holdout_episode: ExperienceEpisode,
    v1: DomainView,
    v2: DomainView,
    observed_conditions: list[str],
    behavior_before: dict[str, str],
    behavior_after: dict[str, str],
    independent_validation_pass: bool,
) -> object:
    claims, reason = retrieve_learned_claims(
        v2,
        applicability_conditions=observed_conditions,
        observed_conditions=observed_conditions,
    )
    return record_application(
        receipt=receipt,
        target_episode_id=holdout_episode.episode_id,
        retrieved_claims=claims,
        retrieval_reason=reason,
        behavior_before=behavior_before,
        behavior_after=behavior_after,
        independent_validation_pass=independent_validation_pass,
        regression_pass=True,
    )
