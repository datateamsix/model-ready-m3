"""Typed presentation contract between PreM3 intelligence and human output.

Machine structure is owned here. Markdown is a fallback renderer, not the
parser or source of enum values. RESPONSE_STYLE_GUIDE.md is the canonical
human-readable presentation standard.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.intelligence.contracts import DecisionClass, KnowledgeClass, ResponsibleActor

RESPONSE_ARCHITECTURE_VERSION = "1.0.0"
TOP_FINDINGS_MIN = 3
TOP_FINDINGS_MAX = 5
DEFAULT_QUESTION_DISPLAY_LIMIT = 5
FULL_OUTPUT_QA_HARNESS = "deferred"

FORBIDDEN_PRIMARY_SUBSTRINGS = (
    "Traceback (most recent call last)",
    'File "',
    "stack trace",
)

FORBIDDEN_CAUSAL_CLAIMS = (
    "promotion is a confounder",
    "this is definitely a confounder",
    "proves causality",
    "this channel caused",
    "the model will fail",
)


class ResponseType(StrEnum):
    PRODUCT_INTELLIGENCE = "PRODUCT_INTELLIGENCE"
    DEFINITION = "DEFINITION"
    RUN_STATUS = "RUN_STATUS"
    ASSESSMENT = "ASSESSMENT"
    ADVISORY = "ADVISORY"
    INSIGHT = "INSIGHT"
    GUIDED_REMEDIATION = "GUIDED_REMEDIATION"
    DATA_ACQUISITION = "DATA_ACQUISITION"
    SEMANTIC_QUESTION = "SEMANTIC_QUESTION"
    SEMANTIC_INTERVIEW = "SEMANTIC_INTERVIEW"
    MODELING_FEASIBILITY = "MODELING_FEASIBILITY"
    SCOPE_SCENARIO = "SCOPE_SCENARIO"
    OFFICIAL_MERIDIAN_EDA = "OFFICIAL_MERIDIAN_EDA"
    MODEL_READY = "MODEL_READY"
    BLOCKED = "BLOCKED"
    EXECUTION_RESULT = "EXECUTION_RESULT"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    COMPARISON = "COMPARISON"
    DATA_SUMMARY = "DATA_SUMMARY"
    HANDOFF = "HANDOFF"
    DOMAIN_VIEW = "DOMAIN_VIEW"
    LEARNING = "LEARNING"
    SOURCE_AUTHORITY = "SOURCE_AUTHORITY"
    JUDGE_DEMO = "JUDGE_DEMO"


class PresentationStatus(StrEnum):
    PASS = "PASS"
    READY = "READY"
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
    USER_ACTION_REQUIRED = "USER_ACTION_REQUIRED"
    MODELER_REVIEW_REQUIRED = "MODELER_REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    COMPLETE = "COMPLETE"


class SectionType(StrEnum):
    SUMMARY = "SUMMARY"
    METRICS = "METRICS"
    FINDINGS = "FINDINGS"
    INSIGHTS = "INSIGHTS"
    GUIDANCE = "GUIDANCE"
    ACTIONS = "ACTIONS"
    QUESTIONS = "QUESTIONS"
    SCENARIOS = "SCENARIOS"
    FEASIBILITY = "FEASIBILITY"
    OFFICIAL_MERIDIAN = "OFFICIAL_MERIDIAN"
    PROOF = "PROOF"
    SOURCES = "SOURCES"
    TECHNICAL_DETAILS = "TECHNICAL_DETAILS"


class ResponseOrigin(StrEnum):
    RUN_EVIDENCE = "RUN_EVIDENCE"
    OFFICIAL_MERIDIAN = "OFFICIAL_MERIDIAN"
    DOMAIN_VIEW = "DOMAIN_VIEW"
    HUMAN_CONTEXT = "HUMAN_CONTEXT"
    PREM3_INTERPRETATION = "PREM3_INTERPRETATION"
    PRODUCT_CONTEXT = "PRODUCT_CONTEXT"


class DisclosureLevel(StrEnum):
    SUMMARY = "SUMMARY"
    DETAILS = "DETAILS"
    PROOF = "PROOF"


class ProductBehavior(StrEnum):
    ASSESS = "ASSESS"
    ADVISE = "ADVISE"
    INSIGHT = "INSIGHT"
    GUIDE = "GUIDE"


KNOWLEDGE_AUTHORITY_LABELS = {
    KnowledgeClass.MERIDIAN_NORMATIVE: "Official Meridian requirement",
    KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC: "PreM3 deterministic diagnostic",
    KnowledgeClass.MMM_EVIDENCE_HEURISTIC: "MMM best-practice heuristic",
    KnowledgeClass.MMM_JUDGMENT: "Modeler judgment",
    KnowledgeClass.PREM3_POLICY_BLOCKER: "PreM3 policy blocker",
    KnowledgeClass.DOMAIN_VIEW_LEARNED: "DOMAIN_VIEW learned pattern",
}

UI_COMPONENT_MAP = {
    "status": "StatusHeader",
    "metrics": "MetricRow",
    "findings": "FindingCard",
    "insights": "InsightCard",
    "actions": "ActionCard",
    "questions": "QuestionCard",
    "scenarios": "ScenarioCard",
    "official_meridian": "MeridianFindingCard",
    "authority": "SourceBadge",
    "proof": "ProofDrawer",
    "run_status": "Timeline",
    "learning": "LearningDiff",
}


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    origin: ResponseOrigin
    path: str
    label: str
    value: str | int | float | bool | None = None
    artifact: str | None = None


class AuthorityPresentation(BaseModel):
    """Compact label plus full machine authority. Do not flatten the two."""

    model_config = ConfigDict(extra="forbid")

    knowledge_class: KnowledgeClass
    decision_class: DecisionClass
    knowledge_label: str
    decision_label: str
    rule_id: str | None = None
    source_url: str | None = None
    blocks_model_ready: bool = False


class ResponseMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    label: str
    value: str | int | float | bool | None
    evidence_id: str
    unit: str | None = None


class ResponseFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    title: str
    observed_fact: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    interpretation: str | None = None
    why_it_matters: str
    knowledge_class: KnowledgeClass
    decision_class: DecisionClass
    knowledge_authority_label: str
    decision_authority_label: str
    disposition: PresentationStatus
    origin: ResponseOrigin
    affected_entities: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    related_action_ids: list[str] = Field(default_factory=list)
    technical_proof_refs: list[str] = Field(default_factory=list)
    official_severity: str | None = None
    official_finding_text: str | None = None
    prem3_interpretation: str | None = None


class ResponseInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insight_id: str
    statement: str
    evidence_ids: list[str] = Field(default_factory=list)
    implication: str
    do_not_claim: str | None = None
    origin: ResponseOrigin = ResponseOrigin.PREM3_INTERPRETATION


class ResponseAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    action: str
    owner: ResponsibleActor
    reason: str
    knowledge_class: KnowledgeClass | None = None
    decision_class: DecisionClass
    can_prem3_execute: bool
    requires_approval: bool = False
    retry_condition: str | None = None
    related_finding_ids: list[str] = Field(default_factory=list)


class SemanticQuestionCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    question: str
    why_asking: str
    triggered_by: str
    trigger_evidence: list[EvidenceRef] = Field(default_factory=list)
    what_changes: str
    owner: ResponsibleActor
    decision_authority: DecisionClass
    affected_scope: list[str] = Field(default_factory=list)
    open_human_question: bool = False
    prior_provenance: str | None = None


class ScenarioView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    title: str
    assumption: str
    baseline_to_scenario: list[dict[str, str]] = Field(default_factory=list)
    what_improves: str
    what_does_not_change: str
    authority: str
    required_review: str
    read_only: bool = True
    production_data_changed: bool = False


class FeasibilityRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str
    status: PresentationStatus
    evidence: str
    evidence_ids: list[str] = Field(default_factory=list)


class OfficialMeridianView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    severity: Literal["ERROR", "ATTENTION", "INFO"]
    finding_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    prem3_why_it_matters: str | None = None
    prem3_guidance: str | None = None
    next_action_id: str | None = None


class ResponseSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_type: SectionType
    title: str
    body: str | None = None
    visible_at: DisclosureLevel = DisclosureLevel.SUMMARY


class ProofBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipts: list[EvidenceRef] = Field(default_factory=list)
    fingerprints: dict[str, str] = Field(default_factory=dict)
    bigquery_endpoint: str | None = None
    rule_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    artifact_uris: list[str] = Field(default_factory=list)
    official_meridian_raw: list[dict[str, Any]] = Field(default_factory=list)


class TechnicalDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str | None = None
    fingerprints: dict[str, str] = Field(default_factory=dict)
    registry_ids: list[str] = Field(default_factory=list)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    storage_paths: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)
    raw_enums: dict[str, str] = Field(default_factory=dict)
    raw_error: str | None = None


class ModelReadyGateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_status: str
    bigquery_verified: bool
    content_fingerprint_matched: bool
    official_meridian_eda_complete: bool
    official_error_count: int
    handoff_persisted: bool
    review_recommended: bool = False
    evidence_ids: list[str] = Field(default_factory=list)


class DisclosurePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_level: DisclosureLevel = DisclosureLevel.SUMMARY
    summary_finding_ids: list[str] = Field(default_factory=list)
    additional_finding_count: int = 0
    view_all_available: bool = False
    question_display_limit: int = DEFAULT_QUESTION_DISPLAY_LIMIT


class AccuracyHook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_ids: list[str] = Field(default_factory=list)
    numeric_paths: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)


class SemanticsHook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: ResponseType
    status: PresentationStatus
    knowledge_classes: list[KnowledgeClass] = Field(default_factory=list)
    decision_classes: list[DecisionClass] = Field(default_factory=list)
    owners: list[ResponsibleActor] = Field(default_factory=list)
    causal_restraint_required: bool = False


class FormatHook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_title: bool
    has_summary: bool
    section_types: list[SectionType] = Field(default_factory=list)
    technical_details_separated: bool = True
    ui_components: list[str] = Field(default_factory=list)


class OutputQaHooks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accuracy: AccuracyHook
    semantics: SemanticsHook
    format: FormatHook
    consistency_group: str | None = None
    harness_status: Literal["deferred"] = "deferred"


class OutputEvaluationCase(BaseModel):
    """Future Agent Output Evaluation Harness case. Not a live corpus."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    user_prompt: str
    run_context: dict[str, Any] | None = None
    expected_response_type: ResponseType
    required_facts: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    expected_authority: list[str] = Field(default_factory=list)
    expected_actions: list[str] = Field(default_factory=list)
    expected_owners: list[ResponsibleActor] = Field(default_factory=list)
    expected_status: PresentationStatus
    format_expectations: list[str] = Field(default_factory=list)
    semantic_expectations: list[str] = Field(default_factory=list)
    consistency_group: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class ResponseIntent(BaseModel):
    """Explicit routing input. Do not overfit free-text classification."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    has_run_context: bool = False
    audience: Literal["user", "judge"] = "user"
    response_type: ResponseType | None = None


class StructuredResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: ResponseType
    title: str
    summary: str
    status: PresentationStatus
    sections: list[ResponseSection] = Field(default_factory=list)
    metrics: list[ResponseMetric] = Field(default_factory=list)
    findings: list[ResponseFinding] = Field(default_factory=list)
    insights: list[ResponseInsight] = Field(default_factory=list)
    actions: list[ResponseAction] = Field(default_factory=list)
    questions: list[SemanticQuestionCard] = Field(default_factory=list)
    scenarios: list[ScenarioView] = Field(default_factory=list)
    feasibility_rows: list[FeasibilityRow] = Field(default_factory=list)
    official_meridian: list[OfficialMeridianView] = Field(default_factory=list)
    authority: list[AuthorityPresentation] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    proof: ProofBundle = Field(default_factory=ProofBundle)
    technical_details: TechnicalDetails = Field(default_factory=TechnicalDetails)
    product_behaviors: list[ProductBehavior] = Field(default_factory=list)
    disclosure: DisclosurePlan = Field(default_factory=DisclosurePlan)
    qa_hooks: OutputQaHooks | None = None
    gate_evidence: ModelReadyGateEvidence | None = None
    blocked_reason: str | None = None
    retry_condition: str | None = None
    consistency_group: str | None = None
    architecture_version: str = RESPONSE_ARCHITECTURE_VERSION

    @model_validator(mode="after")
    def _validate_contract(self) -> StructuredResponse:
        from app.response.validate import validate_structured_response

        validate_structured_response(self)
        return self
