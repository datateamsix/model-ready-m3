"""Typed MEL contracts. These extend existing DOMAIN_VIEW and LearningReceipt enums."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.core.contracts import utc_now
from app.domain.intelligence.models import ClaimScope, LearnedAuthority


class EpisodeTerminalOutcome(StrEnum):
    MODEL_READY = "MODEL_READY"
    USER_REQUIRED = "USER_REQUIRED"
    EDA_BLOCKED = "EDA_BLOCKED"
    CONTRACT_BLOCKED = "CONTRACT_BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class LessonType(StrEnum):
    REMEDIATION_PATTERN = "remediation_pattern"
    EDA_ROUTING = "eda_routing"
    EDA_INTERPRETATION_PATTERN = "eda_interpretation_pattern"
    MODELER_HANDOFF_PATTERN = "modeler_handoff_pattern"
    PRECHECK_COVERAGE_PATTERN = "precheck_coverage_pattern"
    PRE_MODELING_FAILURE_PATTERN = "pre_modeling_failure_pattern"
    TOOL_EFFICACY = "tool_efficacy"
    PROVIDER_SCHEMA_PATTERN = "provider_schema_pattern"
    SEMANTIC_QUESTION_ROUTING = "semantic_question_routing"
    RESPONSE_PRIORITIZATION_PATTERN = "response_prioritization_pattern"


class AlignmentRelation(StrEnum):
    CONFIRMED = "CONFIRMED"
    RELATED = "RELATED"
    NEW_EDA_SIGNAL = "NEW_EDA_SIGNAL"
    PRECHECK_ONLY = "PRECHECK_ONLY"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class NoveltyClass(StrEnum):
    NOVEL = "NOVEL"
    DUPLICATE = "DUPLICATE"
    MORE_SPECIFIC = "MORE_SPECIFIC"
    MORE_GENERAL = "MORE_GENERAL"
    CONFLICTING = "CONFLICTING"
    SUPERSEDES = "SUPERSEDES"
    ALREADY_KNOWN = "ALREADY_KNOWN"
    NOT_EXPERIENTIAL_NOVELTY = "NOT_EXPERIENTIAL_NOVELTY"


class EvaluationDecision(StrEnum):
    PROMOTE = "PROMOTE"
    REJECT = "REJECT"
    HOLD_FOR_MORE_EVIDENCE = "HOLD_FOR_MORE_EVIDENCE"
    GOVERNANCE_REQUIRED = "GOVERNANCE_REQUIRED"


class EvaluationStageName(StrEnum):
    STRUCTURE = "STRUCTURE"
    NOVELTY = "NOVELTY"
    SOURCE_AUTHORITY = "SOURCE_AUTHORITY"
    POLICY = "POLICY"
    SCOPE = "SCOPE"
    EVIDENCE = "EVIDENCE"
    GENERALIZATION = "GENERALIZATION"
    PRIVACY = "PRIVACY"
    BEHAVIOR_EFFECT = "BEHAVIOR_EFFECT"
    REGRESSION = "REGRESSION"
    PROMOTION_AUTHORITY = "PROMOTION_AUTHORITY"


class DomainViewRegistryStatus(StrEnum):
    STAGED = "STAGED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"


class LearningReceiptEnum(StrEnum):
    EXPERIENCE_LEARNED = "EXPERIENCE_LEARNED"
    EXPERIENCE_APPLIED = "EXPERIENCE_APPLIED"
    MEL_EVALUATION_FAILED = "MEL_EVALUATION_FAILED"
    NO_SAFE_PROMOTABLE_LESSON = "NO_SAFE_PROMOTABLE_LESSON"
    NO_MATCHING_HOLDOUT_APPLICATION = "NO_MATCHING_HOLDOUT_APPLICATION"
    APPLICATION_FAILED = "APPLICATION_FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvidenceRef(BaseModel):
    kind: str
    path: str
    fingerprint: str | None = None
    present: bool = True


class AlignmentRecord(BaseModel):
    prem3_finding_id: str | None = None
    meridian_finding_id: str | None = None
    relation: AlignmentRelation
    reason: str
    proposed_by: str = "DETERMINISTIC"
    validation_status: str = "RECORDED"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ExpectationStatus(StrEnum):
    NOT_RECORDED = "NOT_RECORDED"
    RECORDED = "RECORDED"


class ReflectionSurface(StrEnum):
    KNOWN_AT_DECISION_TIME = "KNOWN_AT_DECISION_TIME"
    OBSERVED = "OBSERVED"
    DETERMINED = "DETERMINED"
    BELIEVED = "BELIEVED"
    ALLOWED = "ALLOWED"
    UNKNOWN = "UNKNOWN"
    EXPECTED = "EXPECTED"
    ACTUAL_OUTCOME = "ACTUAL_OUTCOME"
    CONFIRMED = "CONFIRMED"
    MISSED = "MISSED"
    INCOMPLETE = "INCOMPLETE"
    HUMAN_ADDED = "HUMAN_ADDED"
    MERIDIAN_ADDED = "MERIDIAN_ADDED"
    EFFECTIVE_ACTIONS = "EFFECTIVE_ACTIONS"
    INEFFECTIVE_OR_UNNECESSARY_ACTIONS = "INEFFECTIVE_OR_UNNECESSARY_ACTIONS"
    SURPRISES = "SURPRISES"
    POSSIBLE_IMPROVEMENTS = "POSSIBLE_IMPROVEMENTS"


class ReflectionItem(BaseModel):
    item_id: str
    surface: ReflectionSurface
    statement: str
    origin: str
    evidence_refs: list[str] = Field(default_factory=list)


class ExperienceReflection(BaseModel):
    """Reflective evidence only. Has no operational authority."""

    reflection_id: str
    episode_id: str
    run_id: str
    episode_fingerprint: str
    domain_view_version_used: str
    domain_view_fingerprint_used: str
    created_at: str
    reflection_version: str = "1.0.0"
    known_at_decision_time: list[ReflectionItem] = Field(default_factory=list)
    observed: list[ReflectionItem] = Field(default_factory=list)
    determined: list[ReflectionItem] = Field(default_factory=list)
    believed: list[ReflectionItem] = Field(default_factory=list)
    allowed: list[ReflectionItem] = Field(default_factory=list)
    unknown: list[ReflectionItem] = Field(default_factory=list)
    expected: list[ReflectionItem] = Field(default_factory=list)
    expected_status: ExpectationStatus = ExpectationStatus.NOT_RECORDED
    actual_outcome: list[ReflectionItem] = Field(default_factory=list)
    confirmed: list[ReflectionItem] = Field(default_factory=list)
    missed: list[ReflectionItem] = Field(default_factory=list)
    incomplete: list[ReflectionItem] = Field(default_factory=list)
    human_added: list[ReflectionItem] = Field(default_factory=list)
    meridian_added: list[ReflectionItem] = Field(default_factory=list)
    effective_actions: list[ReflectionItem] = Field(default_factory=list)
    ineffective_or_unnecessary_actions: list[ReflectionItem] = Field(default_factory=list)
    surprises: list[ReflectionItem] = Field(default_factory=list)
    possible_improvements: list[ReflectionItem] = Field(default_factory=list)
    generalization_risk: str
    reflection_summary: str
    content_fingerprint: str
    operational_authority: bool = False

    def model_post_init(self, __context: Any) -> None:
        self.operational_authority = False


class ExperienceEpisode(BaseModel):
    episode_id: str
    run_id: str
    organization_id: str | None = None
    workspace_id: str | None = None
    project_id: str | None = None
    package_identity: str | None = None
    episode_started_at: str
    episode_closed_at: str
    terminal_outcome: EpisodeTerminalOutcome
    input_fingerprint: str | None = None
    model_input_fingerprint: str | None = None
    domain_view_version: str
    domain_view_fingerprint: str
    intelligence_version: str | None = None
    runtime_revision: str | None = None
    agent_version: str | None = None
    response_contract_version: str | None = None
    meridian_version: str | None = None
    evidence_index: list[EvidenceRef] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    alignments: list[AlignmentRecord] = Field(default_factory=list)
    learning_eligible: bool = True
    content_fingerprint: str
    holdout: bool = False
    reflection_id: str | None = None


class CandidateLesson(BaseModel):
    candidate_lesson_id: str
    source_episode_ids: list[str]
    lesson_type: LessonType
    statement: str
    problem_pattern: str
    applicability_conditions: list[str] = Field(default_factory=list)
    scope: ClaimScope = Field(default_factory=ClaimScope)
    requested_authority: LearnedAuthority
    expected_behavior_change: str
    supporting_evidence_refs: list[str] = Field(default_factory=list)
    contradictory_evidence_refs: list[str] = Field(default_factory=list)
    meridian_corroboration: bool = False
    known_exclusions: list[str] = Field(default_factory=list)
    known_risks: list[str] = Field(default_factory=list)
    candidate_created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    candidate_creator: str = "MEL_DETERMINISTIC_EXTRACTOR"
    evaluation_status: EvaluationDecision | None = None
    content_fingerprint: str | None = None
    synthetic_fixture: bool = False
    source_reflection_id: str | None = None


class StageResult(BaseModel):
    stage: EvaluationStageName
    passed: bool
    outcome: str
    detail: str


class LessonEvaluation(BaseModel):
    evaluation_id: str
    candidate_lesson_id: str
    source_episode_ids: list[str]
    stages: list[StageResult] = Field(default_factory=list)
    novelty: NoveltyClass | None = None
    decision: EvaluationDecision
    reason: str
    content_fingerprint: str


class RegressionPlan(BaseModel):
    matching_cases: list[str] = Field(default_factory=list)
    non_matching_cases: list[str] = Field(default_factory=list)
    known_exclusions: list[str] = Field(default_factory=list)
    guardrail_tests: list[str] = Field(default_factory=list)
    model_ready_invariance: bool = True
    meridian_origin_separation: bool = True
    privacy_tests: bool = True


class RegressionResult(BaseModel):
    passed: bool
    matching_case_changed: bool | None = None
    non_matching_case_stable: bool | None = None
    model_ready_stable: bool = True
    meridian_origin_stable: bool = True
    numeric_diagnostics_stable: bool = True
    detail: str = ""


class PromotionReceipt(BaseModel):
    candidate_lesson_id: str
    source_episode_ids: list[str]
    evaluation_id: str
    old_domain_view_version: str
    old_domain_view_fingerprint: str
    new_domain_view_version: str
    new_domain_view_fingerprint: str
    promoted_claim_id: str
    lesson_type: LessonType
    scope: ClaimScope
    authority: LearnedAuthority
    behavior_effect: str
    regression_result: RegressionResult
    promotion_timestamp: str
    receipt_type: LearningReceiptEnum = LearningReceiptEnum.EXPERIENCE_LEARNED


class DomainViewRegistryEntry(BaseModel):
    domain_view_version: str
    fingerprint: str
    previous_version: str | None = None
    status: DomainViewRegistryStatus
    content_uri: str | None = None
    base_context_version: str | None = None
    rule_registry_version: str | None = None
    promoted_lesson_ids: list[str] = Field(default_factory=list)
    created_at: str
    activated_at: str | None = None
    revoked_at: str | None = None


class HoldoutManifest(BaseModel):
    dataset_identity: str
    classification: str
    seed: int | None = None
    created_at: str
    input_package_fingerprint: str
    schema_fingerprint: str
    purpose: str = "MEL_HOLDOUT"
    sealed_before_candidate_extraction: bool = True
    lesson_ids_visible_at_seal: list[str] = Field(default_factory=list)
    generator_version: str | None = None


class ExperienceApplication(BaseModel):
    application_id: str
    lesson_id: str
    domain_view_claim_id: str
    source_learning_episode_ids: list[str]
    target_episode_id: str
    domain_view_version: str
    applicability_match: bool
    retrieved: bool
    retrieved_claim_ids: list[str] = Field(default_factory=list)
    retrieval_reason: str | None = None
    behavior_before: dict[str, Any] = Field(default_factory=dict)
    behavior_after: dict[str, Any] = Field(default_factory=dict)
    expected_behavior_change: str
    observed_behavior_change: str | None = None
    validation_result: str
    regression_result: str
    created_at: str
    receipt_type: LearningReceiptEnum | None = None


class MelError(ValueError):
    """Fail-closed MEL evaluation or promotion error."""
