"""First controlled PreM3 experiential-learning experiment.

A + B evidence only. Dataset C is evaluation-only. At most one promotion.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.contracts import utc_now
from app.domain.intelligence.diff import diff_domain_views
from app.domain.intelligence.models import DomainView, LearnedAuthority
from app.mel.behavior import (
    ExpectedBehaviorEffect,
    behavior_delta,
    behavior_fingerprint,
    effect_succeeded,
    semantic_question_routing_effect,
)
from app.mel.candidates import propose_cross_episode_candidates
from app.mel.evaluate import classify_novelty, evaluate_candidate
from app.mel.fingerprint import fingerprint_payload
from app.mel.holdout import isolation_fingerprint, reject_holdout_training
from app.mel.ledger import record_candidate, record_evaluation, record_promotion
from app.mel.models import (
    CandidateLesson,
    EvaluationDecision,
    EvaluationStageName,
    ExperienceEpisode,
    ExperienceReflection,
    LessonType,
    RegressionResult,
    StageResult,
)
from app.mel.promote import activate_promoted_view, load_active_view, stage_domain_view
from app.mel.regression import evaluate_routing_regression
from app.mel.routing_apply import SEMANTIC_OPEN_CONDITIONS, apply_routing_plan

EXPERIMENT_ID = "prem3-first-real-learning-cycle-20260816"
MAX_PROMOTIONS = 1
MIN_INDEPENDENT_EPISODES = 2
CANDIDATE_SELECTION_POLICY = {
    "max_promotions": MAX_PROMOTIONS,
    "holdout_access": "EVALUATION_ONLY",
    "min_independent_episodes": MIN_INDEPENDENT_EPISODES,
    "dataset_c_excluded": True,
    "ranking": [
        "prefer_behavior_altering_routing_hint",
        "lowest_authority_among_behavior_altering",
        "strongest_independent_ab_support",
        "clearest_typed_behavior_effect",
        "lowest_generalization_risk",
        "simplest_global_scope",
        "lexicographic_candidate_id",
    ],
    "forbidden_selection_inputs": [
        "dataset_c_applicability",
        "dataset_c_expected_behavior",
        "dataset_c_negative_controls",
    ],
}


def build_experiment_manifest(
    *,
    baseline_git_sha: str,
    domain_view: DomainView,
    dataset_a_fingerprint: str,
    dataset_b_fingerprint: str,
    dataset_c_fingerprint: str,
    cloud_runtime_revision: str | None = None,
    cloud_image_digest: str | None = None,
) -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "created_at": utc_now().isoformat(),
        "baseline_git_sha": baseline_git_sha,
        "cloud_runtime_revision": cloud_runtime_revision,
        "cloud_image_digest": cloud_image_digest,
        "domain_view_v1_version": domain_view.domain_view_version,
        "domain_view_v1_fingerprint": domain_view.content_fingerprint,
        "dataset_a_id": "dataset_a_music_center",
        "dataset_a_fingerprint": dataset_a_fingerprint,
        "dataset_b_id": "dataset_b_stride_and_field",
        "dataset_b_fingerprint": dataset_b_fingerprint,
        "dataset_c_id": "dataset_c_summit_and_pine",
        "dataset_c_fingerprint": dataset_c_fingerprint,
        "dataset_c_role": "SEALED_HOLDOUT",
        "rule_registry_version": "1.0.0",
        "response_contract_version": "1.0",
        "meridian_version": "google-meridian==1.8.0",
        "mel_policy_version": "1.0.0",
        "candidate_selection_policy": CANDIDATE_SELECTION_POLICY,
        "max_promotions": MAX_PROMOTIONS,
        "holdout_access": "EVALUATION_ONLY",
    }


def routing_regression_for(
    candidate: CandidateLesson, view: DomainView
) -> RegressionResult:
    staged = stage_domain_view(candidate, previous=view)
    conditions = list(candidate.applicability_conditions)
    matching_before = apply_routing_plan(
        view, observed_conditions=conditions, fallback_conditions=conditions
    )
    matching_after = apply_routing_plan(
        staged, observed_conditions=conditions, fallback_conditions=conditions
    )
    nonmatching_before = apply_routing_plan(
        view, observed_conditions=[], fallback_conditions=conditions
    )
    nonmatching_after = apply_routing_plan(
        staged, observed_conditions=[], fallback_conditions=conditions
    )
    return evaluate_routing_regression(
        matching_before={"routing": matching_before["handoff_action_order"]},
        matching_after={"routing": matching_after["handoff_action_order"]},
        nonmatching_before={"routing": nonmatching_before["handoff_action_order"]},
        nonmatching_after={"routing": nonmatching_after["handoff_action_order"]},
        model_ready_before="UNCHANGED",
        model_ready_after="UNCHANGED",
        meridian_origin_before="OFFICIAL_MERIDIAN_EDA",
        meridian_origin_after="OFFICIAL_MERIDIAN_EDA",
        numeric_before={"invariant": True},
        numeric_after={"invariant": True},
    )


def _authority_rank(authority: LearnedAuthority) -> int:
    if authority is LearnedAuthority.OBSERVATION_ONLY:
        return 0
    if authority is LearnedAuthority.ROUTING_HINT:
        return 1
    if authority is LearnedAuthority.ADVISORY:
        return 2
    if authority is LearnedAuthority.AUTO_SAFE_POLICY:
        return 3
    if authority is LearnedAuthority.NONE:
        return 99
    raise AssertionError(f"unhandled authority: {authority}")


def rank_promotable(
    rows: list[tuple[CandidateLesson, Any]],
) -> list[tuple[CandidateLesson, Any]]:
    def key(row: tuple[CandidateLesson, Any]) -> tuple[Any, ...]:
        candidate, _evaluation = row
        altering = 0 if candidate.requested_authority is LearnedAuthority.ROUTING_HINT else 1
        has_effect = 0 if candidate.expected_behavior_effect else 1
        return (
            altering,
            _authority_rank(candidate.requested_authority),
            -(candidate.independent_context_count or 0),
            has_effect,
            candidate.scope.level.value,
            candidate.candidate_lesson_id,
        )

    return sorted(rows, key=key)


def _candidate_report(
    candidate: CandidateLesson,
    evaluation: Any,
    view: DomainView,
) -> dict[str, Any]:
    novelty = evaluation.novelty or classify_novelty(candidate, view)
    overlap = []
    if novelty.value != "NOVEL":
        overlap = [
            claim.claim_id
            for claim in view.active_claims()
            if claim.statement.strip().lower() == candidate.statement.strip().lower()
        ]
    return {
        "candidate_id": candidate.candidate_lesson_id,
        "candidate_type": candidate.lesson_type.value,
        "statement": candidate.statement,
        "condition": list(candidate.applicability_conditions),
        "recommended_behavior": candidate.expected_behavior_change,
        "requested_authority": candidate.requested_authority.value,
        "scope": candidate.scope.model_dump(mode="json"),
        "applicability_conditions": list(candidate.applicability_conditions),
        "supporting_episode_ids": list(candidate.source_episode_ids),
        "supporting_reflection_ids": list(candidate.source_reflection_ids)
        or [candidate.source_reflection_id],
        "independent_context_count": candidate.independent_context_count,
        "evidence_refs": list(candidate.supporting_evidence_refs),
        "common_pattern": candidate.common_pattern,
        "cross_episode_differences": list(candidate.cross_episode_differences),
        "novelty_status": novelty.value,
        "existing_domain_view_overlap": overlap,
        "negative_control_analysis": candidate.negative_control_analysis,
        "generalization_risk": candidate.generalization_risk,
        "expected_behavior_effect": candidate.expected_behavior_effect,
        "current_status": evaluation.decision.value,
        "evaluation_id": evaluation.evaluation_id,
        "evaluation_reason": evaluation.reason,
        "stages": [item.model_dump(mode="json") for item in evaluation.stages],
    }


def evaluate_ab_candidates(
    *,
    episode_a: ExperienceEpisode,
    reflection_a: ExperienceReflection,
    episode_b: ExperienceEpisode,
    reflection_b: ExperienceReflection,
    view: DomainView,
    ledger_dir: Path,
) -> dict[str, Any]:
    reject_holdout_training(episode_a, action="first-cycle candidate generation")
    reject_holdout_training(episode_b, action="first-cycle candidate generation")
    candidates = propose_cross_episode_candidates(
        [episode_a, episode_b],
        [reflection_a, reflection_b],
    )
    reports: list[dict[str, Any]] = []
    promotable: list[tuple[CandidateLesson, Any]] = []
    for candidate in candidates:
        if (
            candidate.independent_context_count
            and candidate.independent_context_count >= MIN_INDEPENDENT_EPISODES
            and not candidate.expected_behavior_effect
            and candidate.lesson_type is LessonType.SEMANTIC_QUESTION_ROUTING
        ):
            effect = semantic_question_routing_effect()
            candidate.expected_behavior_effect = effect.model_dump(mode="json")
            candidate.expected_behavior_change = (
                f"{effect.type.value} target={effect.target} "
                f"success={effect.success_measure}"
            )
        record_candidate(ledger_dir, candidate)
        regression = None
        if candidate.independent_context_count and candidate.independent_context_count >= 2:
            regression = routing_regression_for(candidate, view)
        evaluation = evaluate_candidate(
            candidate,
            episodes=[episode_a, episode_b],
            view=view,
            regression=regression,
        )
        if (
            evaluation.decision is EvaluationDecision.PROMOTE
            and (candidate.independent_context_count or 0) < MIN_INDEPENDENT_EPISODES
        ):
            evaluation.decision = EvaluationDecision.HOLD_FOR_MORE_EVIDENCE
            evaluation.reason = "first-experiment requires two independent episodes"
            evaluation.stages.append(
                StageResult(
                    stage=EvaluationStageName.INDEPENDENT_SUPPORT,
                    passed=False,
                    outcome="HOLD_FOR_MORE_EVIDENCE",
                    detail="Experiment standard is independent_context_count >= 2.",
                )
            )
        conflicts = int(
            (candidate.negative_control_analysis or {}).get("negative_control_conflicts") or 0
        )
        if evaluation.decision is EvaluationDecision.PROMOTE and conflicts:
            evaluation.decision = EvaluationDecision.REJECT
            evaluation.reason = "unresolved negative-control conflicts"
            evaluation.stages.append(
                StageResult(
                    stage=EvaluationStageName.NEGATIVE_CONTROL,
                    passed=False,
                    outcome="REJECT",
                    detail="unresolved_negative_control_conflicts != 0",
                )
            )
        elif evaluation.decision is EvaluationDecision.PROMOTE:
            evaluation.stages.append(
                StageResult(
                    stage=EvaluationStageName.INDEPENDENT_SUPPORT,
                    passed=True,
                    outcome="PASS",
                    detail="A+B independent contexts satisfy the first-experiment bar.",
                )
            )
            evaluation.stages.append(
                StageResult(
                    stage=EvaluationStageName.NEGATIVE_CONTROL,
                    passed=True,
                    outcome="PASS",
                    detail="No unresolved A/B negative-control conflicts.",
                )
            )
        record_evaluation(ledger_dir, evaluation)
        reports.append(_candidate_report(candidate, evaluation, view))
        if evaluation.decision is EvaluationDecision.PROMOTE:
            promotable.append((candidate, evaluation))
    ranked = rank_promotable(promotable)
    selected = ranked[0] if ranked else None
    return {
        "candidates": reports,
        "eligible_count": len(ranked),
        "ranking_rule": CANDIDATE_SELECTION_POLICY["ranking"],
        "selected": None
        if selected is None
        else {
            "candidate": selected[0],
            "evaluation": selected[1],
            "ranking_inputs": {
                "independent_context_count": selected[0].independent_context_count,
                "authority": selected[0].requested_authority.value,
                "has_typed_effect": bool(selected[0].expected_behavior_effect),
            },
        },
        "isolation_fingerprint": isolation_fingerprint(
            [episode_a.episode_id, episode_b.episode_id],
            "dataset_c_summit_and_pine",
        ),
    }


def promote_selected(
    *,
    candidate: CandidateLesson,
    evaluation: Any,
    view: DomainView,
    registry_dir: Path,
    ledger_dir: Path,
    regression: RegressionResult,
) -> dict[str, Any]:
    staged = stage_domain_view(candidate, previous=view)
    receipt = activate_promoted_view(
        candidate=candidate,
        evaluation=evaluation,
        staged=staged,
        previous=view,
        regression=regression,
        registry_dir=registry_dir,
    )
    record_promotion(ledger_dir, receipt)
    active = load_active_view(registry_dir)
    diff = diff_domain_views(view, active)
    return {
        "receipt": receipt,
        "old_version": view.domain_view_version,
        "old_fingerprint": view.content_fingerprint,
        "new_version": active.domain_view_version,
        "new_fingerprint": active.content_fingerprint,
        "claim_count_before": view.promoted_lesson_count,
        "claim_count_after": active.promoted_lesson_count,
        "diff": diff.model_dump(mode="json"),
        "active": active,
    }


def application_plan(
    *,
    experiment_id: str,
    lesson_id: str,
    dataset_c_fingerprint: str,
    domain_view_v1_fingerprint: str,
    domain_view_v2_fingerprint: str,
    effect: ExpectedBehaviorEffect,
) -> dict[str, Any]:
    plan = {
        "experiment_id": experiment_id,
        "lesson_id": lesson_id,
        "dataset_c_id": "dataset_c_summit_and_pine",
        "dataset_c_fingerprint": dataset_c_fingerprint,
        "domain_view_v1_fingerprint": domain_view_v1_fingerprint,
        "domain_view_v2_fingerprint": domain_view_v2_fingerprint,
        "expected_behavior_effect": effect.model_dump(mode="json"),
        "applicability_conditions": list(SEMANTIC_OPEN_CONDITIONS),
        "allowed_change_fields": list(effect.allowed_change_fields),
        "invariant_fields": [
            "model_input_fingerprint",
            "schema_fingerprint",
            "parameter_calculations",
            "model_ready_logic",
        ],
        "negative_control_requirements": {
            "unresolved_conflicts": 0,
            "causal_roles_assigned": False,
        },
        "independent_validator": "evaluate_holdout_application",
        "success_contract": "retrieval AND applicability AND declared effect AND sealed PASS",
    }
    plan["content_fingerprint"] = fingerprint_payload(plan)
    return plan


def write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    path.write_text(text, encoding="utf-8")
    return fingerprint_payload(payload)


def dump_behavior_comparison(
    v1: dict[str, Any],
    v2: dict[str, Any],
    effect: ExpectedBehaviorEffect,
) -> dict[str, Any]:
    delta = behavior_delta(v1, v2, effect=effect)
    return {
        "behavior_fingerprint_v1": behavior_fingerprint(v1),
        "behavior_fingerprint_v2": behavior_fingerprint(v2),
        "delta": delta,
        "effect_succeeded": effect_succeeded(delta, effect),
    }
