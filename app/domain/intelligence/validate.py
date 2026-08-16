"""Fail-closed validation for DOMAIN_VIEW claims and promoted-lesson inputs."""

from __future__ import annotations

import re

from app.domain.intelligence.models import (
    ClaimScope,
    DomainViewClaim,
    DomainViewError,
    KnowledgeClass,
    KnowledgeLayer,
    LearnedAuthority,
    PromotedLessonInput,
    PromotionStatus,
    ScopeLevel,
)

FORBIDDEN_GLOBAL_MARKERS = (
    "organization_id",
    "customer_id",
    "account_id",
    "workspace_id",
    "run_id",
    "dataset a has",
    "524 rows",
    "kpi=",
)

FORBIDDEN_FINAL_MODELING = (
    "final prior",
    "final priors",
    "sample_posterior",
    "final modelspec",
    "knots for future final",
    "use 130 knots for future final",
)

ALWAYS_ZERO_MISSING = re.compile(
    r"missing (media|provider rows).*(always|automatically).*(zero|0)",
    re.IGNORECASE,
)
ALWAYS_CAUSAL_ROLE = re.compile(
    r"\balways\b.+\b(mediator|confounder|predictor)\b",
    re.IGNORECASE,
)
NEGATIVE_MEDIA_OK = re.compile(r"negative media is acceptable", re.IGNORECASE)


def layer_for_class(knowledge_class: KnowledgeClass) -> KnowledgeLayer:
    mapping = {
        KnowledgeClass.MERIDIAN_NORMATIVE: KnowledgeLayer.MERIDIAN_NORMATIVE,
        KnowledgeClass.PREM3_POLICY: KnowledgeLayer.PREM3_POLICY,
        KnowledgeClass.PREM3_POLICY_BLOCKER: KnowledgeLayer.PREM3_POLICY,
        KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC: KnowledgeLayer.VERIFIED_DOMAIN_GUIDANCE,
        KnowledgeClass.MMM_EVIDENCE_HEURISTIC: KnowledgeLayer.VERIFIED_DOMAIN_GUIDANCE,
        KnowledgeClass.DESIGN_DEFAULT: KnowledgeLayer.VERIFIED_DOMAIN_GUIDANCE,
        KnowledgeClass.MMM_JUDGMENT: KnowledgeLayer.VERIFIED_DOMAIN_GUIDANCE,
        KnowledgeClass.VALIDATED_EXPERIENCE_PATTERN: KnowledgeLayer.VALIDATED_EXPERIENCE_PATTERN,
        KnowledgeClass.ADVISORY_LEARNED_PATTERN: KnowledgeLayer.ADVISORY_LEARNED_PATTERN,
        KnowledgeClass.OBSERVATION: KnowledgeLayer.OBSERVATION,
    }
    return mapping[knowledge_class]


def validate_claim_identity(claim_ids: list[str]) -> None:
    seen: set[str] = set()
    for claim_id in claim_ids:
        if not claim_id or not claim_id.strip():
            raise DomainViewError("claim_id is required")
        if claim_id in seen:
            raise DomainViewError(f"duplicate claim_id: {claim_id}")
        seen.add(claim_id)


def _text(value: str) -> str:
    return value.strip().lower()


def reject_privacy_leak(statement: str, scope: ClaimScope) -> None:
    lowered = _text(statement)
    if any(marker in lowered for marker in FORBIDDEN_GLOBAL_MARKERS):
        raise DomainViewError(
            "global DOMAIN_VIEW cannot contain customer, run, or account identifiers"
        )
    if scope.level is ScopeLevel.GLOBAL and scope.value and "@" in scope.value:
        raise DomainViewError("global scope value cannot contain an account identifier")


def reject_run_fact(scope: ClaimScope, statement: str) -> None:
    if scope.level is ScopeLevel.RUN:
        raise DomainViewError("run evidence is not global domain knowledge")
    if re.search(r"\b\d+\s+rows\b", statement, re.IGNORECASE):
        raise DomainViewError("run-specific row counts cannot enter global DOMAIN_VIEW")


def reject_org_into_global(scope: ClaimScope) -> None:
    if scope.level is ScopeLevel.ORGANIZATION:
        raise DomainViewError("organization-scoped knowledge cannot enter global DOMAIN_VIEW")


def reject_forbidden_learning(lesson: PromotedLessonInput) -> None:
    statement = lesson.statement
    lowered = _text(statement)
    if NEGATIVE_MEDIA_OK.search(statement):
        raise DomainViewError("learned claim cannot override Meridian non-negative media rule")
    if ALWAYS_ZERO_MISSING.search(statement):
        raise DomainViewError("learned claim cannot bypass missing-media safety policy")
    if ALWAYS_CAUSAL_ROLE.search(statement):
        raise DomainViewError("causal role cannot be learned solely as a universal rule")
    if any(token in lowered for token in FORBIDDEN_FINAL_MODELING):
        raise DomainViewError("final priors or final ModelSpec cannot be learned autonomously")
    if lesson.authority is LearnedAuthority.AUTO_SAFE_POLICY and any(
        token in lowered for token in ("prior", "knot", "modelspec", "posterior")
    ):
        raise DomainViewError("AUTO_SAFE_POLICY cannot cover final modeling configuration")


def reject_normative_conflict(lesson: PromotedLessonInput, existing: list[DomainViewClaim]) -> None:
    lowered = _text(lesson.statement)
    for claim in existing:
        if claim.layer is not KnowledgeLayer.MERIDIAN_NORMATIVE:
            continue
        if "non-negative" in _text(claim.statement) and "negative media is acceptable" in lowered:
            raise DomainViewError("learned claim conflicts with MERIDIAN_NORMATIVE")
        if claim.claim_id in lesson.statement:
            raise DomainViewError("learned claim cannot override a named normative rule")


def validate_promoted_lesson(
    lesson: PromotedLessonInput,
    existing: list[DomainViewClaim],
) -> None:
    if lesson.promotion_status is not PromotionStatus.PROMOTED:
        raise DomainViewError("only PROMOTED lessons may enter DOMAIN_VIEW")
    if lesson.regression_status.upper() not in {"PASSED", "PASS"}:
        raise DomainViewError("promoted lesson must have passing regression status")
    reject_org_into_global(lesson.scope)
    reject_run_fact(lesson.scope, lesson.statement)
    reject_privacy_leak(lesson.statement, lesson.scope)
    reject_forbidden_learning(lesson)
    reject_normative_conflict(lesson, existing)
    if lesson.authority is LearnedAuthority.NONE:
        raise DomainViewError("promoted lesson must declare a learned authority")
    if lesson.knowledge_class is KnowledgeClass.MERIDIAN_NORMATIVE:
        raise DomainViewError("experience cannot mint MERIDIAN_NORMATIVE claims")


def lesson_is_eligible(lesson: PromotedLessonInput) -> bool:
    return lesson.promotion_status is PromotionStatus.PROMOTED
