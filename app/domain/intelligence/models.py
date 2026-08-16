"""Typed DOMAIN_VIEW contracts.

DOMAIN_VIEW is the versioned operational knowledge PreM3 is currently
justified and authorized to use. It is not raw memory.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeLayer(StrEnum):
    MERIDIAN_NORMATIVE = "MERIDIAN_NORMATIVE"
    PREM3_POLICY = "PREM3_POLICY"
    VERIFIED_DOMAIN_GUIDANCE = "VERIFIED_DOMAIN_GUIDANCE"
    VALIDATED_EXPERIENCE_PATTERN = "VALIDATED_EXPERIENCE_PATTERN"
    ADVISORY_LEARNED_PATTERN = "ADVISORY_LEARNED_PATTERN"
    OBSERVATION = "OBSERVATION"


class KnowledgeClass(StrEnum):
    MERIDIAN_NORMATIVE = "MERIDIAN_NORMATIVE"
    PREM3_POLICY = "PREM3_POLICY"
    PREM3_POLICY_BLOCKER = "PREM3_POLICY_BLOCKER"
    PREM3_DETERMINISTIC_DIAGNOSTIC = "PREM3_DETERMINISTIC_DIAGNOSTIC"
    MMM_EVIDENCE_HEURISTIC = "MMM_EVIDENCE_HEURISTIC"
    MMM_JUDGMENT = "MMM_JUDGMENT"
    DESIGN_DEFAULT = "DESIGN_DEFAULT"
    VALIDATED_EXPERIENCE_PATTERN = "VALIDATED_EXPERIENCE_PATTERN"
    ADVISORY_LEARNED_PATTERN = "ADVISORY_LEARNED_PATTERN"
    OBSERVATION = "OBSERVATION"


class LearnedAuthority(StrEnum):
    OBSERVATION_ONLY = "OBSERVATION_ONLY"
    ADVISORY = "ADVISORY"
    ROUTING_HINT = "ROUTING_HINT"
    AUTO_SAFE_POLICY = "AUTO_SAFE_POLICY"
    NONE = "NONE"


class SourceType(StrEnum):
    OFFICIAL_SOURCE = "OFFICIAL_SOURCE"
    PREM3_POLICY = "PREM3_POLICY"
    FOUNDATIONAL_EVIDENCE = "FOUNDATIONAL_EVIDENCE"
    CROSS_FRAMEWORK_EVIDENCE = "CROSS_FRAMEWORK_EVIDENCE"
    PROMOTED_EXPERIENCE = "PROMOTED_EXPERIENCE"


class ScopeLevel(StrEnum):
    GLOBAL = "GLOBAL"
    ORGANIZATION = "ORGANIZATION"
    WORKSPACE = "WORKSPACE"
    PROVIDER = "PROVIDER"
    REPORT_TYPE = "REPORT_TYPE"
    SCHEMA_PATTERN = "SCHEMA_PATTERN"
    VARIABLE_CLASS = "VARIABLE_CLASS"
    CHANNEL_TYPE = "CHANNEL_TYPE"
    MODEL_TYPE = "MODEL_TYPE"
    RUN = "RUN"


class ClaimStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    REJECTED = "REJECTED"


class PromotionStatus(StrEnum):
    PROMOTED = "PROMOTED"
    CANDIDATE = "CANDIDATE"
    REJECTED = "REJECTED"
    FAILED_REGRESSION = "FAILED_REGRESSION"


class ChangeType(StrEnum):
    INITIAL_COMPILE = "INITIAL_COMPILE"
    OFFICIAL_SOURCE_UPDATE = "OFFICIAL_SOURCE_UPDATE"
    POLICY_UPDATE = "POLICY_UPDATE"
    HEURISTIC_UPDATE = "HEURISTIC_UPDATE"
    EXPERIENCE_LEARNED = "EXPERIENCE_LEARNED"
    LESSON_AUTHORITY_CHANGE = "LESSON_AUTHORITY_CHANGE"
    LESSON_SCOPE_CHANGE = "LESSON_SCOPE_CHANGE"
    LESSON_REVOKED = "LESSON_REVOKED"
    LESSON_SUPERSEDED = "LESSON_SUPERSEDED"


class ClaimScope(BaseModel):
    level: ScopeLevel = ScopeLevel.GLOBAL
    value: str | None = None


class ExperienceProvenance(BaseModel):
    candidate_lesson_id: str | None = None
    episode_ids: list[str] = Field(default_factory=list)
    evaluation_evidence: list[str] = Field(default_factory=list)
    regression_evidence: list[str] = Field(default_factory=list)
    promotion_receipt_id: str | None = None
    promotion_timestamp: str | None = None


class DomainViewClaim(BaseModel):
    claim_id: str
    statement: str
    knowledge_class: KnowledgeClass
    layer: KnowledgeLayer
    authority: LearnedAuthority = LearnedAuthority.NONE
    scope: ClaimScope = Field(default_factory=ClaimScope)
    source_type: SourceType
    source_refs: list[str] = Field(default_factory=list)
    source_version: str | None = None
    evidence: list[str] = Field(default_factory=list)
    regression_status: str = "NOT_APPLICABLE"
    behavior_effect: str | None = None
    first_added_at: str | None = None
    last_validated_at: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    status: ClaimStatus = ClaimStatus.ACTIVE
    prohibited_overrides: list[str] = Field(default_factory=list)
    experience_provenance: ExperienceProvenance | None = None


class PromotedLessonInput(BaseModel):
    """Input contract for a MEL-promoted lesson. MEL is not implemented here."""

    lesson_id: str
    statement: str
    knowledge_class: KnowledgeClass = KnowledgeClass.VALIDATED_EXPERIENCE_PATTERN
    authority: LearnedAuthority
    scope: ClaimScope = Field(default_factory=ClaimScope)
    source_refs: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    regression_status: str = "PASSED"
    behavior_effect: str | None = None
    promotion_status: PromotionStatus = PromotionStatus.PROMOTED
    experience_provenance: ExperienceProvenance | None = None
    last_validated_at: str | None = None


class DomainViewSourceVersions(BaseModel):
    intelligence_version: str
    product_context_version: str
    mmm_boot_context_version: str
    rule_registry_version: str
    intelligence_registry_version: str
    source_verification_date: str
    meridian_worker_pin: str


class DomainView(BaseModel):
    domain_view_version: str
    generated_at: str
    source_versions: DomainViewSourceVersions
    promoted_lesson_set_version: str
    promoted_lesson_count: int
    content_fingerprint: str
    previous_domain_view_version: str | None = None
    status: str = "ACTIVE"
    claims: list[DomainViewClaim] = Field(default_factory=list)

    def active_claims(self) -> list[DomainViewClaim]:
        return [claim for claim in self.claims if claim.status is ClaimStatus.ACTIVE]


class DomainViewChangeReceipt(BaseModel):
    previous_version: str | None
    new_version: str
    previous_fingerprint: str | None
    new_fingerprint: str
    change_types: list[ChangeType] = Field(default_factory=list)
    changed_claim_ids: list[str] = Field(default_factory=list)
    source_reason: str
    experience_lesson_ids: list[str] = Field(default_factory=list)
    approved_by: str | None = None
    timestamp: str


class DomainViewDiff(BaseModel):
    added_claim_ids: list[str] = Field(default_factory=list)
    removed_claim_ids: list[str] = Field(default_factory=list)
    modified_claim_ids: list[str] = Field(default_factory=list)
    authority_changes: list[dict[str, Any]] = Field(default_factory=list)
    scope_changes: list[dict[str, Any]] = Field(default_factory=list)
    source_updates: list[str] = Field(default_factory=list)
    experiential_learning_changes: list[str] = Field(default_factory=list)
    change_types: list[ChangeType] = Field(default_factory=list)


class DomainViewError(ValueError):
    """Fail-closed DOMAIN_VIEW validation or compile error."""
