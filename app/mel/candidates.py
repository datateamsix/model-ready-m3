"""Candidate extraction from ExperienceReflection plus referenced episode evidence.

Gemini may propose candidates later. This extractor is deterministic and
does not promote. Possible improvements in a reflection are not lessons.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.domain.intelligence.models import ClaimScope, LearnedAuthority, ScopeLevel
from app.mel.fingerprint import fingerprint_payload
from app.mel.holdout import reject_holdout_training
from app.mel.models import (
    CandidateLesson,
    DatasetRole,
    ExperienceEpisode,
    ExperienceReflection,
    LessonType,
    MelError,
    ReflectionRole,
)


def candidate_fingerprint(candidate: CandidateLesson) -> str:
    return fingerprint_payload(
        {
            "statement": candidate.statement.strip().lower(),
            "lesson_type": candidate.lesson_type.value,
            "scope": candidate.scope.model_dump(mode="json"),
            "requested_authority": candidate.requested_authority.value,
            "applicability_conditions": list(candidate.applicability_conditions),
            "expected_behavior_change": candidate.expected_behavior_change,
            "source_reflection_id": candidate.source_reflection_id,
        }
    )


def validate_candidate_structure(candidate: CandidateLesson) -> None:
    if not candidate.source_episode_ids:
        raise MelError("candidate requires source episode")
    if not candidate.statement.strip():
        raise MelError("candidate requires statement")
    if not candidate.expected_behavior_change.strip():
        raise MelError("candidate requires expected behavior change")
    if not candidate.applicability_conditions:
        raise MelError("candidate requires applicability conditions")
    if candidate.scope.level is ScopeLevel.RUN:
        raise MelError("run evidence is not a reusable lesson")
    if candidate.requested_authority is LearnedAuthority.NONE:
        raise MelError("candidate must declare requested authority")


def _id_for(episode_id: str, kind: str, statement: str) -> str:
    digest = hashlib.sha256(f"{episode_id}:{kind}:{statement}".encode()).hexdigest()[:12]
    return f"cand-{kind}-{digest}"


def propose_candidates_from_episode(
    episode: ExperienceEpisode,
    reflection: ExperienceReflection | None = None,
) -> list[CandidateLesson]:
    reject_holdout_training(episode, action="candidate extraction")
    if reflection is None:
        raise MelError("production candidate extraction requires ExperienceReflection")
    return propose_candidates_from_reflection(reflection, episode=episode)


def propose_candidates_from_reflection(
    reflection: ExperienceReflection,
    *,
    episode: ExperienceEpisode,
) -> list[CandidateLesson]:
    if reflection.episode_id != episode.episode_id:
        raise MelError("reflection does not reference this episode")
    if reflection.episode_fingerprint != episode.content_fingerprint:
        raise MelError("reflection fingerprint does not match episode")
    reject_holdout_training(episode, action="candidate extraction")
    if reflection.reflection_role is ReflectionRole.EVALUATION_ONLY:
        raise MelError(
            "REJECTED_HOLDOUT_INPUT: evaluation-only reflections cannot train MEL"
        )
    candidates: list[CandidateLesson] = []
    if reflection.missed or reflection.meridian_added:
        statement = (
            "When official Meridian EDA reports a check type that PreM3 pre-EDA did "
            "not surface, prioritize the official finding in the modeler handoff "
            "and keep PreM3 diagnostics visually separate."
        )
        candidates.append(
            _routing_candidate(
                episode,
                reflection,
                lesson_type=LessonType.PRECHECK_COVERAGE_PATTERN,
                statement=statement,
                problem="Official Meridian can surface signals PreM3 pre-EDA does not evaluate.",
                conditions=[
                    "official Meridian EDA complete",
                    "at least one NEW_EDA_SIGNAL alignment",
                ],
                evidence=["reflection", "alignments", "official_eda"],
                meridian=True,
            )
        )
    if any(item.item_id == "unknown-semantic" for item in reflection.unknown):
        statement = (
            "When semantic-readiness questions are generated for a run, surface those "
            "questions before advisory spend or parameter commentary so causal gaps "
            "are not treated as settled numeric facts."
        )
        candidates.append(
            _routing_candidate(
                episode,
                reflection,
                lesson_type=LessonType.SEMANTIC_QUESTION_ROUTING,
                statement=statement,
                problem="Numeric diagnostics can crowd out unresolved causal questions.",
                conditions=[
                    "semantic readiness interview persisted",
                    "at least one open semantic question",
                ],
                evidence=["reflection", "semantic"],
                meridian=False,
            )
        )
    if any(
        item.statement == "USER_REQUIRED" for item in reflection.actual_outcome
    ):
        statement = (
            "When a pre-modeling assignment stops for a source or approval gap, "
            "prioritize the identified actor and missing evidence in guided "
            "remediation before proposing new diagnostics."
        )
        candidates.append(
            _routing_candidate(
                episode,
                reflection,
                lesson_type=LessonType.PRE_MODELING_FAILURE_PATTERN,
                statement=statement,
                problem="Blocked episodes still contain reusable resolution-routing evidence.",
                conditions=["terminal outcome USER_REQUIRED"],
                evidence=["reflection", "guided_remediation", "issues"],
                meridian=False,
            )
        )
    for candidate in candidates:
        candidate.content_fingerprint = candidate_fingerprint(candidate)
        validate_candidate_structure(candidate)
    return candidates


def _routing_candidate(
    episode: ExperienceEpisode,
    reflection: ExperienceReflection,
    *,
    lesson_type: LessonType,
    statement: str,
    problem: str,
    conditions: list[str],
    evidence: list[str],
    meridian: bool,
) -> CandidateLesson:
    return CandidateLesson(
        candidate_lesson_id=_id_for(episode.episode_id, lesson_type.value, statement),
        source_episode_ids=[episode.episode_id],
        source_reflection_id=reflection.reflection_id,
        lesson_type=lesson_type,
        statement=statement,
        problem_pattern=problem,
        applicability_conditions=conditions,
        scope=ClaimScope(level=ScopeLevel.GLOBAL),
        requested_authority=LearnedAuthority.ROUTING_HINT,
        expected_behavior_change=(
            "Change finding, question, or handoff routing order on matching cases "
            "without changing MODEL_READY or official Meridian severity."
        ),
        supporting_evidence_refs=evidence,
        meridian_corroboration=meridian,
        candidate_creator="MEL_DETERMINISTIC_EXTRACTOR",
    )


def propose_cross_episode_candidates(
    episodes: list[ExperienceEpisode],
    reflections: list[ExperienceReflection],
) -> list[CandidateLesson]:
    """Report per-episode candidates plus optional A+B merged routing candidates.

    Does not promote. Does not inspect holdout episodes. A matching pattern
    across independent contexts is evidence to *report*, not a required lesson.
    """
    if len(episodes) < 2:
        raise MelError("cross-episode candidates require at least two episodes")
    if any(episode.holdout for episode in episodes) or any(
        episode.dataset_role is DatasetRole.SEALED_HOLDOUT for episode in episodes
    ):
        raise MelError(
            "REJECTED_HOLDOUT_INPUT: cross-episode candidate generation must not use holdout episodes"
        )
    by_id = {episode.episode_id: episode for episode in episodes}
    per_episode: list[tuple[ExperienceEpisode, ExperienceReflection, list[CandidateLesson]]] = []
    for reflection in reflections:
        episode = by_id.get(reflection.episode_id)
        if episode is None:
            raise MelError("reflection episode is not in the provided episode set")
        extracted = propose_candidates_from_reflection(reflection, episode=episode)
        per_episode.append((episode, reflection, extracted))

    reported: list[CandidateLesson] = []
    by_type: dict[
        LessonType, list[tuple[ExperienceEpisode, ExperienceReflection, CandidateLesson]]
    ] = {}
    for episode, reflection, extracted in per_episode:
        reported.extend(extracted)
        for candidate in extracted:
            by_type.setdefault(candidate.lesson_type, []).append((episode, reflection, candidate))

    merged: list[CandidateLesson] = []
    for lesson_type, group in by_type.items():
        episode_ids = sorted({episode.episode_id for episode, _, _ in group})
        if len(episode_ids) < 2:
            continue
        _, _, base = group[0]
        reflection_ids = [reflection.reflection_id for _, reflection, _ in group]
        businesses = sorted(
            {
                str(
                    episode.summary.get("business")
                    or episode.organization_id
                    or episode.episode_id
                )
                for episode, _, _ in group
            }
        )
        candidate = CandidateLesson(
            candidate_lesson_id=_id_for("+".join(episode_ids), lesson_type.value, base.statement),
            source_episode_ids=episode_ids,
            source_reflection_id=reflection_ids[0],
            source_reflection_ids=reflection_ids,
            lesson_type=lesson_type,
            statement=base.statement,
            problem_pattern=base.problem_pattern,
            applicability_conditions=list(base.applicability_conditions),
            scope=base.scope,
            requested_authority=base.requested_authority,
            expected_behavior_change=base.expected_behavior_change,
            supporting_evidence_refs=list(base.supporting_evidence_refs),
            meridian_corroboration=any(item.meridian_corroboration for _, _, item in group),
            candidate_creator="MEL_DETERMINISTIC_EXTRACTOR",
            independent_context_count=len(episode_ids),
            common_pattern=base.problem_pattern,
            cross_episode_differences=[
                "Independent synthetic businesses and provider mixes",
                f"Observed contexts: {', '.join(businesses)}",
            ],
            generalization_basis=(
                "The same routing pattern appeared in more than one independent "
                "assignment. That is not sufficient by itself to promote."
            ),
        )
        candidate.content_fingerprint = candidate_fingerprint(candidate)
        validate_candidate_structure(candidate)
        merged.append(candidate)
    return reported + merged


def fixture_candidate(**overrides: Any) -> CandidateLesson:
    payload = {
        "candidate_lesson_id": "cand-fixture-routing",
        "source_episode_ids": ["ep-fixture"],
        "source_reflection_id": "ref-fixture",
        "lesson_type": LessonType.SEMANTIC_QUESTION_ROUTING,
        "statement": (
            "When GQV, paid search, and upper-funnel media coexist, trigger semantic "
            "review before treating correlation as a causal role."
        ),
        "problem_pattern": "Correlation can be misread as a causal assignment.",
        "applicability_conditions": [
            "GQV or branded-search proxy present",
            "paid search present",
            "upper-funnel media present",
        ],
        "scope": ClaimScope(level=ScopeLevel.GLOBAL),
        "requested_authority": LearnedAuthority.ROUTING_HINT,
        "expected_behavior_change": (
            "Ask a semantic-readiness question before GQV causal advice."
        ),
        "supporting_evidence_refs": ["semantic", "official_eda"],
        "meridian_corroboration": True,
        "synthetic_fixture": True,
        "candidate_creator": "UNIT_FIXTURE",
    }
    payload.update(overrides)
    candidate = CandidateLesson.model_validate(payload)
    candidate.content_fingerprint = candidate_fingerprint(candidate)
    return candidate
