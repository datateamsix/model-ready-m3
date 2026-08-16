"""Typed contracts for PreM3 computational and semantic run intelligence.

PreM3 pre-EDA findings are not official Meridian EDA findings. Official
ERROR / ATTENTION / INFO remain owned by the isolated Meridian worker.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.contracts import utc_now

CALCULATOR_VERSION = "1.0.0"
FINDING_ORIGIN_PREM3 = "PREM3_PRE_EDA"
VOLATILE_FINGERPRINT_KEYS = frozenset(
    {
        "generated_at",
        "calculated_at",
        "queried_at",
        "recorded_at",
        "query_timestamp",
        "artifact_uris",
    }
)


class FindingOrigin(StrEnum):
    PREM3_PRE_EDA = "PREM3_PRE_EDA"
    OFFICIAL_MERIDIAN_EDA = "OFFICIAL_MERIDIAN_EDA"


class Prem3DiagnosticDisposition(StrEnum):
    PASS = "PASS"
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
    USER_CONTEXT_REQUIRED = "USER_CONTEXT_REQUIRED"
    CONTRACT_FAILURE = "CONTRACT_FAILURE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class KnowledgeClass(StrEnum):
    MERIDIAN_NORMATIVE = "MERIDIAN_NORMATIVE"
    PREM3_DETERMINISTIC_DIAGNOSTIC = "PREM3_DETERMINISTIC_DIAGNOSTIC"
    MMM_EVIDENCE_HEURISTIC = "MMM_EVIDENCE_HEURISTIC"
    MMM_JUDGMENT = "MMM_JUDGMENT"
    PREM3_POLICY_BLOCKER = "PREM3_POLICY_BLOCKER"
    DOMAIN_VIEW_LEARNED = "DOMAIN_VIEW_LEARNED"


class DecisionClass(StrEnum):
    AUTO_BLOCK = "AUTO_BLOCK"
    AUTO_SAFE = "AUTO_SAFE"
    ADVISORY = "ADVISORY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    MODELER_REVIEW_REQUIRED = "MODELER_REVIEW_REQUIRED"
    USER_REQUIRED = "USER_REQUIRED"


class ResponsibleActor(StrEnum):
    PREM3 = "PREM3"
    MARKETER = "MARKETER"
    ANALYST = "ANALYST"
    DATA_ENGINEER = "DATA_ENGINEER"
    MODELER = "MODELER"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class KnotsSource(StrEnum):
    EDA_ONLY_COMPATIBILITY = "EDA_ONLY_COMPATIBILITY"
    PRE_EDA_DIAGNOSTIC_ASSUMPTION = "PRE_EDA_DIAGNOSTIC_ASSUMPTION"
    MODELER_PROVIDED = "MODELER_PROVIDED"


class SourceMode(StrEnum):
    BIGQUERY = "BIGQUERY"
    FIXTURE_ADAPTER = "FIXTURE_ADAPTER"


class MissingnessClass(StrEnum):
    CONFIRMED_INACTIVITY = "CONFIRMED_INACTIVITY"
    SOURCE_CONFIRMED_ZERO = "SOURCE_CONFIRMED_ZERO"
    UNKNOWN_ABSENCE = "UNKNOWN_ABSENCE"
    SOURCE_GAP = "SOURCE_GAP"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class PrePeriodCoverage(StrEnum):
    PRESENT = "PRESENT"
    PARTIAL = "PARTIAL"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class SemanticReadinessStatus(StrEnum):
    CLEAR = "CLEAR"
    QUESTIONS_OPEN = "QUESTIONS_OPEN"
    USER_CONTEXT_REQUIRED = "USER_CONTEXT_REQUIRED"
    MODELER_REVIEW_REQUIRED = "MODELER_REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ComputationalDimension(StrEnum):
    DATA_CONTRACT = "DATA_CONTRACT"
    HISTORY = "HISTORY"
    GEO_COVERAGE = "GEO_COVERAGE"
    PARAMETER_PRESSURE = "PARAMETER_PRESSURE"
    CHANNEL_SPEND_DISTRIBUTION = "CHANNEL_SPEND_DISTRIBUTION"
    CHANNEL_VARIATION = "CHANNEL_VARIATION"
    SPEND_RANGE = "SPEND_RANGE"
    COLLINEARITY = "COLLINEARITY"
    PRE_PERIOD_MEDIA = "PRE_PERIOD_MEDIA"
    MEDIA_SPEND_CONSISTENCY = "MEDIA_SPEND_CONSISTENCY"
    POPULATION_RELATIONSHIPS = "POPULATION_RELATIONSHIPS"
    REACH_FREQUENCY = "REACH_FREQUENCY"
    MISSINGNESS_EVIDENCE = "MISSINGNESS_EVIDENCE"


class FeasibilityDimension(StrEnum):
    DATA_CONTRACT = "DATA_CONTRACT"
    HISTORY = "HISTORY"
    GEO_COVERAGE = "GEO_COVERAGE"
    PARAMETER_PRESSURE = "PARAMETER_PRESSURE"
    CHANNEL_VARIATION = "CHANNEL_VARIATION"
    SPEND_RANGE = "SPEND_RANGE"
    COLLINEARITY = "COLLINEARITY"
    PRE_PERIOD_MEDIA = "PRE_PERIOD_MEDIA"
    CAUSAL_CONTEXT = "CAUSAL_CONTEXT"
    OFFICIAL_MERIDIAN_EDA = "OFFICIAL_MERIDIAN_EDA"


class ScopeScenarioType(StrEnum):
    ADDITIONAL_HISTORY = "ADDITIONAL_HISTORY"
    ADDITIONAL_VALID_GEOS = "ADDITIONAL_VALID_GEOS"
    CANDIDATE_CHANNEL_CONSOLIDATION = "CANDIDATE_CHANNEL_CONSOLIDATION"
    OPTIONAL_NON_CONFOUNDING_VARIABLE_SCOPE = "OPTIONAL_NON_CONFOUNDING_VARIABLE_SCOPE"
    MODELER_REVIEWED_TIME_COMPLEXITY = "MODELER_REVIEWED_TIME_COMPLEXITY"


class IssueFamily(StrEnum):
    DATA_DEFECT = "DATA_DEFECT"
    STRUCTURAL_DATA_GAP = "STRUCTURAL_DATA_GAP"
    DATA_SUFFICIENCY_GAP = "DATA_SUFFICIENCY_GAP"
    PARAMETER_PRESSURE = "PARAMETER_PRESSURE"
    CAUSAL_CONTEXT_GAP = "CAUSAL_CONTEXT_GAP"
    MODELER_SPECIFICATION_REVIEW = "MODELER_SPECIFICATION_REVIEW"
    SOURCE_ACQUISITION_GAP = "SOURCE_ACQUISITION_GAP"


class AuthorityRef(BaseModel):
    knowledge_class: KnowledgeClass
    decision_class: DecisionClass
    rule_id: str | None = None
    source_url: str | None = None
    source_tier: str | None = None
    blocks_model_ready: bool = False
    threshold_authority: str | None = None


class Prem3PreEdaFinding(BaseModel):
    """A PreM3 pre-EDA diagnostic. Never an official Meridian finding."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str
    finding_origin: Literal["PREM3_PRE_EDA"] = FINDING_ORIGIN_PREM3
    dimension: str
    disposition: Prem3DiagnosticDisposition
    knowledge_class: KnowledgeClass
    decision_class: DecisionClass
    title: str
    what_was_calculated: str
    observed_evidence: dict[str, Any] = Field(default_factory=dict)
    why_it_matters: str
    best_practice: str
    recommended_action: str
    responsible_actor: ResponsibleActor
    blocks_model_ready: bool = False
    review_recommended: bool = False
    affected_variables: list[str] = Field(default_factory=list)
    affected_channels: list[str] = Field(default_factory=list)
    source_authority: AuthorityRef | None = None
    formula: str | None = None
    assumptions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("finding_origin")
    @classmethod
    def _prem3_origin(cls, value: str) -> str:
        if value != FINDING_ORIGIN_PREM3:
            raise ValueError("PreM3 findings must use finding_origin=PREM3_PRE_EDA.")
        return value

    @field_validator("disposition")
    @classmethod
    def _not_official_severity(
        cls, value: Prem3DiagnosticDisposition
    ) -> Prem3DiagnosticDisposition:
        if value.value in {"ERROR", "ATTENTION", "INFO"}:
            raise ValueError("Official Meridian severities are not PreM3 dispositions.")
        return value


class SemanticQuestion(BaseModel):
    question_id: str
    question_family: str
    question: str
    why_pre_m3_is_asking: str
    trigger_evidence: dict[str, Any] = Field(default_factory=dict)
    possible_causal_issue: str
    affected_variables: list[str] = Field(default_factory=list)
    affected_channels: list[str] = Field(default_factory=list)
    what_changes_based_on_answer: str
    required_human_role: ResponsibleActor
    decision_class: DecisionClass
    blocks_current_input_if_unresolved: bool = False
    modeler_review_if_unresolved: bool = True
    source_authority: AuthorityRef | None = None
    source_refs: list[str] = Field(default_factory=list)
    status: str = "OPEN"


class SemanticAnswer(BaseModel):
    question_id: str
    answer: str
    actor_role: ResponsibleActor
    recorded_at: datetime = Field(default_factory=utc_now)
    run_id: str
    scope: str = "RUN"
    provenance: str = "EXPLICIT_HUMAN_ANSWER"
    affected_variables: list[str] = Field(default_factory=list)
    resolves_input_semantics: bool = False
    modeler_review_remains: bool = True


class GuidedRemediationItem(BaseModel):
    issue_family: IssueFamily
    finding_id: str | None = None
    what_i_found: str
    why_it_matters: str
    best_practice: str
    insight_from_your_data: str
    what_prem3_can_do: str
    what_you_should_do: str
    modeler_review: str
    next_step: str
    responsible_actor: ResponsibleActor
    knowledge_class: KnowledgeClass
    decision_class: DecisionClass
    source_acquisition: str | None = None


class DimensionalStatus(BaseModel):
    dimension: str
    disposition: Prem3DiagnosticDisposition
    observed_evidence: dict[str, Any] = Field(default_factory=dict)
    authority: AuthorityRef | None = None
    why_it_matters: str
    recommended_review: str
    related_finding_ids: list[str] = Field(default_factory=list)
    related_question_ids: list[str] = Field(default_factory=list)
    review_recommended: bool = False
    blocks_model_ready: bool = False
