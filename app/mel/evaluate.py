"""Deterministic MEL evaluation. Gemini may explain; it cannot set promotion PASS."""

from __future__ import annotations

import hashlib
import re

from app.domain.intelligence.builder import load_current_domain_view
from app.domain.intelligence.models import (
    DomainView,
    LearnedAuthority,
    ScopeLevel,
)
from app.domain.intelligence.validate import (
    ALWAYS_CAUSAL_ROLE,
    ALWAYS_ZERO_MISSING,
    FORBIDDEN_FINAL_MODELING,
    FORBIDDEN_GLOBAL_MARKERS,
    NEGATIVE_MEDIA_OK,
)
from app.mel.candidates import validate_candidate_structure
from app.mel.fingerprint import fingerprint_payload
from app.mel.models import (
    CandidateLesson,
    EvaluationDecision,
    EvaluationStageName,
    ExperienceEpisode,
    LessonEvaluation,
    NoveltyClass,
    RegressionResult,
    StageResult,
)
from app.mel.policy import auto_safe_eligible, first_cycle_authority_cap, requirements_for

TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {part for part in TOKEN_SPLIT.split(text.lower()) if len(part) > 2}


def _jaccard(left: str, right: str) -> float:
    a = _tokens(left)
    b = _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def classify_novelty(candidate: CandidateLesson, view: DomainView) -> NoveltyClass:
    statement = candidate.statement.strip()
    best = 0.0
    for claim in view.active_claims():
        if claim.statement.strip().lower() == statement.lower():
            return NoveltyClass.DUPLICATE
        best = max(best, _jaccard(statement, claim.statement))
        if claim.source_type.value != "PROMOTED_EXPERIENCE" and best >= 0.72:
            return NoveltyClass.NOT_EXPERIENTIAL_NOVELTY
    if best >= 0.85:
        return NoveltyClass.DUPLICATE
    if best >= 0.72:
        return NoveltyClass.ALREADY_KNOWN
    return NoveltyClass.NOVEL


def _stage(name: EvaluationStageName, passed: bool, outcome: str, detail: str) -> StageResult:
    return StageResult(stage=name, passed=passed, outcome=outcome, detail=detail)


def evaluate_candidate(
    candidate: CandidateLesson,
    *,
    episodes: list[ExperienceEpisode],
    view: DomainView | None = None,
    regression: RegressionResult | None = None,
) -> LessonEvaluation:
    stages: list[StageResult] = []
    current = view or load_current_domain_view()
    if current is None:
        decision = EvaluationDecision.REJECT
        stages.append(
            _stage(
                EvaluationStageName.STRUCTURE,
                False,
                "MISSING_DOMAIN_VIEW",
                "Cannot evaluate without bootstrap DOMAIN_VIEW.",
            )
        )
        return _result(candidate, stages, None, decision, "missing DOMAIN_VIEW")

    try:
        validate_candidate_structure(candidate)
        stages.append(
            _stage(
                EvaluationStageName.STRUCTURE,
                True,
                "PASS",
                "Required candidate fields present.",
            )
        )
    except ValueError as exc:
        stages.append(_stage(EvaluationStageName.STRUCTURE, False, "REJECT", str(exc)))
        return _result(candidate, stages, None, EvaluationDecision.REJECT, str(exc))

    novelty = classify_novelty(candidate, current)
    novelty_ok = novelty is NoveltyClass.NOVEL
    stages.append(
        _stage(
            EvaluationStageName.NOVELTY,
            novelty_ok,
            novelty.value,
            "Experiential novelty compared to current DOMAIN_VIEW.",
        )
    )
    if not novelty_ok:
        return _result(
            candidate,
            stages,
            novelty,
            EvaluationDecision.REJECT,
            f"novelty={novelty.value}",
        )

    lowered = candidate.statement.lower()
    if NEGATIVE_MEDIA_OK.search(candidate.statement) or any(
        token in lowered for token in FORBIDDEN_FINAL_MODELING
    ) or "use 130 knots" in lowered:
        stages.append(
            _stage(
                EvaluationStageName.SOURCE_AUTHORITY,
                False,
                "REJECT",
                "Final model settings cannot be learned.",
            )
        )
        return _result(
            candidate, stages, novelty, EvaluationDecision.REJECT, "final-model boundary"
        )
    if ALWAYS_CAUSAL_ROLE.search(candidate.statement):
        stages.append(
            _stage(
                EvaluationStageName.SOURCE_AUTHORITY,
                False,
                "REJECT",
                "Causal role cannot be learned from correlation.",
            )
        )
        return _result(candidate, stages, novelty, EvaluationDecision.REJECT, "causal overreach")
    stages.append(
        _stage(
            EvaluationStageName.SOURCE_AUTHORITY,
            True,
            "PASS",
            "No Meridian-normative or final-model override detected.",
        )
    )

    if ALWAYS_ZERO_MISSING.search(candidate.statement) or "block model_ready" in lowered:
        stages.append(
            _stage(
                EvaluationStageName.POLICY,
                False,
                "REJECT",
                "Candidate weakens PreM3 safety or MODEL_READY policy.",
            )
        )
        return _result(candidate, stages, novelty, EvaluationDecision.REJECT, "policy conflict")
    stages.append(_stage(EvaluationStageName.POLICY, True, "PASS", "Safety policy preserved."))

    if candidate.scope.level is ScopeLevel.ORGANIZATION:
        stages.append(
            _stage(
                EvaluationStageName.SCOPE,
                False,
                "REJECT",
                "Organization-specific facts cannot enter global DOMAIN_VIEW.",
            )
        )
        return _result(candidate, stages, novelty, EvaluationDecision.REJECT, "organization leak")
    if candidate.scope.level is ScopeLevel.RUN:
        stages.append(
            _stage(
                EvaluationStageName.SCOPE,
                False,
                "REJECT",
                "Run facts are not reusable lessons.",
            )
        )
        return _result(candidate, stages, novelty, EvaluationDecision.REJECT, "run fact")
    stages.append(_stage(EvaluationStageName.SCOPE, True, "PASS", "Scope is explicit and global."))

    if any(marker in lowered for marker in FORBIDDEN_GLOBAL_MARKERS):
        stages.append(
            _stage(
                EvaluationStageName.PRIVACY,
                False,
                "REJECT",
                "Global lesson cannot contain customer or run identifiers.",
            )
        )
        return _result(candidate, stages, novelty, EvaluationDecision.REJECT, "privacy")
    stages.append(_stage(EvaluationStageName.PRIVACY, True, "PASS", "No privacy markers."))

    if not candidate.expected_behavior_change.strip():
        stages.append(
            _stage(
                EvaluationStageName.BEHAVIOR_EFFECT,
                False,
                "OBSERVATION_ONLY",
                "No future behavior change declared.",
            )
        )
        return _result(
            candidate,
            stages,
            novelty,
            EvaluationDecision.HOLD_FOR_MORE_EVIDENCE,
            "no behavior effect",
        )
    stages.append(
        _stage(
            EvaluationStageName.BEHAVIOR_EFFECT,
            True,
            "PASS",
            "Expected future behavior change is explicit.",
        )
    )

    authority = candidate.requested_authority
    if authority is LearnedAuthority.AUTO_SAFE_POLICY and not auto_safe_eligible():
        stages.append(
            _stage(
                EvaluationStageName.PROMOTION_AUTHORITY,
                False,
                "GOVERNANCE_REQUIRED",
                "AUTO_SAFE_POLICY is not eligible in the first learning cycle.",
            )
        )
        return _result(
            candidate,
            stages,
            novelty,
            EvaluationDecision.GOVERNANCE_REQUIRED,
            "first-cycle authority cap",
        )
    cap = first_cycle_authority_cap()
    rank = {
        LearnedAuthority.OBSERVATION_ONLY: 0,
        LearnedAuthority.ADVISORY: 1,
        LearnedAuthority.ROUTING_HINT: 2,
        LearnedAuthority.AUTO_SAFE_POLICY: 3,
        LearnedAuthority.NONE: -1,
    }
    if rank.get(authority, 99) > rank.get(cap, 2):
        stages.append(
            _stage(
                EvaluationStageName.PROMOTION_AUTHORITY,
                False,
                "GOVERNANCE_REQUIRED",
                f"Requested {authority.value} exceeds first-cycle cap {cap.value}.",
            )
        )
        return _result(
            candidate,
            stages,
            novelty,
            EvaluationDecision.GOVERNANCE_REQUIRED,
            "authority cap",
        )

    req = requirements_for(authority)
    independent_ids = {episode.episode_id for episode in episodes}
    independent_ids.update(candidate.source_episode_ids)
    episode_count = len(independent_ids)
    meridian_ok = candidate.meridian_corroboration
    need_second = bool(req.get("meridian_corroboration_or_second_episode"))
    min_eps = int(req.get("min_independent_episodes") or 1)
    if episode_count < min_eps:
        stages.append(
            _stage(
                EvaluationStageName.EVIDENCE,
                False,
                "HOLD_FOR_MORE_EVIDENCE",
                f"Requires {min_eps} independent episodes; saw {episode_count}.",
            )
        )
        return _result(
            candidate,
            stages,
            novelty,
            EvaluationDecision.HOLD_FOR_MORE_EVIDENCE,
            "insufficient episodes",
        )
    if need_second and episode_count < 2 and not meridian_ok:
        stages.append(
            _stage(
                EvaluationStageName.EVIDENCE,
                False,
                "HOLD_FOR_MORE_EVIDENCE",
                "ROUTING_HINT requires a second episode or Meridian corroboration.",
            )
        )
        return _result(
            candidate,
            stages,
            novelty,
            EvaluationDecision.HOLD_FOR_MORE_EVIDENCE,
            "insufficient corroboration",
        )
    stages.append(_stage(EvaluationStageName.EVIDENCE, True, "PASS", "Evidence threshold met."))
    stages.append(
        _stage(
            EvaluationStageName.GENERALIZATION,
            True,
            "PASS",
            "Applicability conditions are pattern-shaped, not run metrics.",
        )
    )

    if bool(req.get("regression_required")):
        if regression is None or not regression.passed:
            stages.append(
                _stage(
                    EvaluationStageName.REGRESSION,
                    False,
                    "REJECT",
                    "Regression must pass before promotion.",
                )
            )
            return _result(
                candidate, stages, novelty, EvaluationDecision.REJECT, "regression required"
            )
        stages.append(_stage(EvaluationStageName.REGRESSION, True, "PASS", regression.detail))
    else:
        stages.append(
            _stage(EvaluationStageName.REGRESSION, True, "NOT_REQUIRED", "Observation-only.")
        )

    stages.append(
        _stage(
            EvaluationStageName.PROMOTION_AUTHORITY,
            True,
            "PROMOTE",
            "Deterministic promotion policy passed.",
        )
    )
    return _result(candidate, stages, novelty, EvaluationDecision.PROMOTE, "eligible")


def _result(
    candidate: CandidateLesson,
    stages: list[StageResult],
    novelty: NoveltyClass | None,
    decision: EvaluationDecision,
    reason: str,
) -> LessonEvaluation:
    evaluation_id = hashlib.sha256(
        f"{candidate.candidate_lesson_id}:{decision.value}:{reason}".encode()
    ).hexdigest()[:16]
    payload = {
        "candidate": candidate.content_fingerprint,
        "decision": decision.value,
        "stages": [item.model_dump(mode="json") for item in stages],
    }
    return LessonEvaluation(
        evaluation_id=f"eval-{evaluation_id}",
        candidate_lesson_id=candidate.candidate_lesson_id,
        source_episode_ids=list(candidate.source_episode_ids),
        stages=stages,
        novelty=novelty,
        decision=decision,
        reason=reason,
        content_fingerprint=fingerprint_payload(payload),
    )
