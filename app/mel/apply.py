"""Experience application and EXPERIENCE_APPLIED gate.

Retrieval must be explicit. Behavior change plus independent validation
are required. Gemini cannot self-certify correctness.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.core.contracts import utc_now
from app.domain.intelligence.models import DomainView, DomainViewClaim, SourceType
from app.mel.models import (
    ExperienceApplication,
    LearningReceiptEnum,
    PromotionReceipt,
)


def retrieve_learned_claims(
    view: DomainView,
    *,
    applicability_conditions: list[str],
    observed_conditions: list[str],
) -> tuple[list[DomainViewClaim], str]:
    observed = {item.strip().lower() for item in observed_conditions}
    matched: list[DomainViewClaim] = []
    reasons: list[str] = []
    for claim in view.active_claims():
        if claim.source_type is not SourceType.PROMOTED_EXPERIENCE:
            continue
        needed_raw = list(claim.applicability_conditions or []) or list(
            applicability_conditions
        )
        needed = {item.strip().lower() for item in needed_raw}
        if needed and needed.issubset(observed):
            matched.append(claim)
            reasons.append(f"{claim.claim_id} matched {sorted(needed)}")
    return matched, "; ".join(reasons)


def record_application(
    *,
    receipt: PromotionReceipt,
    target_episode_id: str,
    retrieved_claims: list[DomainViewClaim],
    retrieval_reason: str,
    behavior_before: dict[str, Any],
    behavior_after: dict[str, Any],
    independent_validation_pass: bool,
    regression_pass: bool,
) -> ExperienceApplication:
    retrieved = bool(retrieved_claims)
    claim_ids = [claim.claim_id for claim in retrieved_claims]
    changed = behavior_before != behavior_after
    expected_key = "routing"
    expected_changed = behavior_before.get(expected_key) != behavior_after.get(expected_key)
    if not retrieved:
        enum = LearningReceiptEnum.NOT_APPLICABLE
        validation = "NOT_APPLICABLE"
    elif not changed or not expected_changed:
        enum = LearningReceiptEnum.NOT_APPLICABLE
        validation = "NO_BEHAVIOR_CHANGE"
    elif not independent_validation_pass:
        enum = LearningReceiptEnum.APPLICATION_FAILED
        validation = "VALIDATION_FAILED"
    elif not regression_pass:
        enum = LearningReceiptEnum.APPLICATION_FAILED
        validation = "REGRESSION_FAILED"
    else:
        enum = LearningReceiptEnum.EXPERIENCE_APPLIED
        validation = "PASS"
    digest = hashlib.sha256(f"{receipt.promoted_claim_id}:{target_episode_id}".encode()).hexdigest()
    return ExperienceApplication(
        application_id=f"app-{digest[:16]}",
        lesson_id=receipt.candidate_lesson_id,
        domain_view_claim_id=receipt.promoted_claim_id,
        source_learning_episode_ids=list(receipt.source_episode_ids),
        target_episode_id=target_episode_id,
        domain_view_version=receipt.new_domain_view_version,
        applicability_match=retrieved,
        retrieved=retrieved,
        retrieved_claim_ids=claim_ids,
        retrieval_reason=retrieval_reason or None,
        behavior_before=behavior_before,
        behavior_after=behavior_after,
        expected_behavior_change=receipt.behavior_effect,
        observed_behavior_change=(
            None if not changed else f"{behavior_before} -> {behavior_after}"
        ),
        validation_result=validation,
        regression_result="PASS" if regression_pass else "FAIL",
        created_at=utc_now().isoformat(),
        receipt_type=enum if enum is LearningReceiptEnum.EXPERIENCE_APPLIED else enum,
    )
