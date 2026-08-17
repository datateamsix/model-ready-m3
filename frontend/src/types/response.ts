/**
 * Mirrors app/response/contracts.py (StructuredResponse and friends).
 * Hand-verified field-for-field against the Python source. Markdown /
 * prose is a fallback renderer; this file is the parser-level contract.
 */
import type { DecisionClass, KnowledgeClass, ResponsibleActor } from "./intelligence";

export type ResponseType =
  | "PRODUCT_INTELLIGENCE"
  | "DEFINITION"
  | "RUN_STATUS"
  | "ASSESSMENT"
  | "ADVISORY"
  | "INSIGHT"
  | "GUIDED_REMEDIATION"
  | "DATA_ACQUISITION"
  | "SEMANTIC_QUESTION"
  | "SEMANTIC_INTERVIEW"
  | "MODELING_FEASIBILITY"
  | "SCOPE_SCENARIO"
  | "OFFICIAL_MERIDIAN_EDA"
  | "MODEL_READY"
  | "BLOCKED"
  | "EXECUTION_RESULT"
  | "APPROVAL_REQUIRED"
  | "COMPARISON"
  | "DATA_SUMMARY"
  | "HANDOFF"
  | "DOMAIN_VIEW"
  | "LEARNING"
  | "SOURCE_AUTHORITY"
  | "JUDGE_DEMO";

export type PresentationStatus =
  | "PASS"
  | "READY"
  | "REVIEW_RECOMMENDED"
  | "USER_ACTION_REQUIRED"
  | "MODELER_REVIEW_REQUIRED"
  | "BLOCKED"
  | "PENDING"
  | "NOT_APPLICABLE"
  | "COMPLETE";

export type SectionType =
  | "SUMMARY"
  | "METRICS"
  | "FINDINGS"
  | "INSIGHTS"
  | "GUIDANCE"
  | "ACTIONS"
  | "QUESTIONS"
  | "SCENARIOS"
  | "FEASIBILITY"
  | "OFFICIAL_MERIDIAN"
  | "PROOF"
  | "SOURCES"
  | "TECHNICAL_DETAILS";

export type ResponseOrigin =
  | "RUN_EVIDENCE"
  | "OFFICIAL_MERIDIAN"
  | "DOMAIN_VIEW"
  | "HUMAN_CONTEXT"
  | "PREM3_INTERPRETATION"
  | "PRODUCT_CONTEXT";

export type DisclosureLevel = "SUMMARY" | "DETAILS" | "PROOF";
export type ProductBehavior = "ASSESS" | "ADVISE" | "INSIGHT" | "GUIDE";

export interface EvidenceRef {
  evidence_id: string;
  origin: ResponseOrigin;
  path: string;
  label: string;
  value: string | number | boolean | null;
  artifact: string | null;
}

export interface AuthorityPresentation {
  knowledge_class: KnowledgeClass;
  decision_class: DecisionClass;
  knowledge_label: string;
  decision_label: string;
  rule_id: string | null;
  source_url: string | null;
  blocks_model_ready: boolean;
}

export interface ResponseMetric {
  metric_id: string;
  label: string;
  value: string | number | boolean | null;
  evidence_id: string;
  unit: string | null;
}

export interface ResponseFinding {
  finding_id: string;
  title: string;
  observed_fact: string;
  evidence: EvidenceRef[];
  interpretation: string | null;
  why_it_matters: string;
  knowledge_class: KnowledgeClass;
  decision_class: DecisionClass;
  knowledge_authority_label: string;
  decision_authority_label: string;
  disposition: PresentationStatus;
  origin: ResponseOrigin;
  affected_entities: string[];
  source_refs: string[];
  related_action_ids: string[];
  technical_proof_refs: string[];
  official_severity: string | null;
  official_finding_text: string | null;
  prem3_interpretation: string | null;
}

export interface ResponseInsight {
  insight_id: string;
  statement: string;
  evidence_ids: string[];
  implication: string;
  do_not_claim: string | null;
  origin: ResponseOrigin;
}

export interface ResponseAction {
  action_id: string;
  action: string;
  owner: ResponsibleActor;
  reason: string;
  knowledge_class: KnowledgeClass | null;
  decision_class: DecisionClass;
  can_prem3_execute: boolean;
  requires_approval: boolean;
  retry_condition: string | null;
  related_finding_ids: string[];
}

export interface SemanticQuestionCard {
  question_id: string;
  question: string;
  why_asking: string;
  triggered_by: string;
  trigger_evidence: EvidenceRef[];
  what_changes: string;
  owner: ResponsibleActor;
  decision_authority: DecisionClass;
  affected_scope: string[];
  open_human_question: boolean;
  prior_provenance: string | null;
}

export interface ScenarioView {
  scenario_id: string;
  title: string;
  assumption: string;
  baseline_to_scenario: Record<string, string>[];
  what_improves: string;
  what_does_not_change: string;
  authority: string;
  required_review: string;
  read_only: boolean;
  production_data_changed: boolean;
}

export interface FeasibilityRow {
  dimension: string;
  status: PresentationStatus;
  evidence: string;
  evidence_ids: string[];
}

export interface OfficialMeridianView {
  finding_id: string;
  severity: "ERROR" | "ATTENTION" | "INFO";
  finding_text: string;
  metadata: Record<string, unknown>;
  prem3_why_it_matters: string | null;
  prem3_guidance: string | null;
  next_action_id: string | null;
}

export interface ResponseSection {
  section_type: SectionType;
  title: string;
  body: string | null;
  visible_at: DisclosureLevel;
}

export interface ProofBundle {
  receipts: EvidenceRef[];
  fingerprints: Record<string, string>;
  bigquery_endpoint: string | null;
  rule_ids: string[];
  source_refs: string[];
  artifact_uris: string[];
  official_meridian_raw: Record<string, unknown>[];
}

export interface TechnicalDetails {
  run_id: string | null;
  fingerprints: Record<string, string>;
  registry_ids: string[];
  artifact_hashes: Record<string, string>;
  storage_paths: string[];
  tool_names: string[];
  raw_enums: Record<string, string>;
  raw_error: string | null;
}

export interface ModelReadyGateEvidence {
  gate_status: string;
  bigquery_verified: boolean;
  content_fingerprint_matched: boolean;
  official_meridian_eda_complete: boolean;
  official_error_count: number;
  handoff_persisted: boolean;
  review_recommended: boolean;
  evidence_ids: string[];
}

export interface DisclosurePlan {
  default_level: DisclosureLevel;
  summary_finding_ids: string[];
  additional_finding_count: number;
  view_all_available: boolean;
  question_display_limit: number;
}

export interface OutputQaHooks {
  accuracy: {
    evidence_ids: string[];
    numeric_paths: string[];
    artifact_refs: string[];
  };
  semantics: {
    response_type: ResponseType;
    status: PresentationStatus;
    knowledge_classes: KnowledgeClass[];
    decision_classes: DecisionClass[];
    owners: ResponsibleActor[];
    causal_restraint_required: boolean;
  };
  format: {
    has_title: boolean;
    has_summary: boolean;
    section_types: SectionType[];
    technical_details_separated: boolean;
    ui_components: string[];
  };
  consistency_group: string | null;
  harness_status: "deferred";
}

export interface StructuredResponse {
  response_type: ResponseType;
  title: string;
  summary: string;
  status: PresentationStatus;
  sections: ResponseSection[];
  metrics: ResponseMetric[];
  findings: ResponseFinding[];
  insights: ResponseInsight[];
  actions: ResponseAction[];
  questions: SemanticQuestionCard[];
  scenarios: ScenarioView[];
  feasibility_rows: FeasibilityRow[];
  official_meridian: OfficialMeridianView[];
  authority: AuthorityPresentation[];
  sources: string[];
  proof: ProofBundle;
  technical_details: TechnicalDetails;
  product_behaviors: ProductBehavior[];
  disclosure: DisclosurePlan;
  qa_hooks: OutputQaHooks | null;
  gate_evidence: ModelReadyGateEvidence | null;
  blocked_reason: string | null;
  retry_condition: string | null;
  consistency_group: string | null;
  architecture_version: string;
}
