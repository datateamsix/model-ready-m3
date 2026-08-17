/**
 * Mirrors the UI-relevant subset of app/mel/models.py. Hand-verified
 * field-for-field against the Python source. Deliberately omits the MEL
 * evaluation-pipeline internals (CandidateLesson, LessonEvaluation,
 * RegressionPlan, DomainViewRegistryEntry, HoldoutManifest) — nothing in
 * the component inventory renders them; only episodes, reflections, and
 * the two receipt types (proof of learning / proof of application) are
 * surfaced to the run workspace.
 */
import type { ClaimScope, LearnedAuthority } from "./domain-view";

export type EpisodeTerminalOutcome =
  | "MODEL_READY"
  | "USER_REQUIRED"
  | "EDA_BLOCKED"
  | "CONTRACT_BLOCKED"
  | "FAILED"
  | "CANCELLED";

/**
 * Distinguishes training-eligible episodes from sealed holdout episodes.
 * Dataset C (Summit & Pine) episodes must render as SEALED_HOLDOUT and are
 * never presented as training data — see the plan's truth-preservation
 * rules.
 */
export type DatasetRole = "TRAINING_EXPERIENCE" | "LEARNING_EVIDENCE" | "SEALED_HOLDOUT";

/** Whether a reflection was produced for training use or evaluation only (e.g. holdout episodes). */
export type ReflectionRole = "TRAINING" | "EVALUATION_ONLY";

export type ReflectionSurface =
  | "KNOWN_AT_DECISION_TIME"
  | "OBSERVED"
  | "DETERMINED"
  | "BELIEVED"
  | "ALLOWED"
  | "UNKNOWN"
  | "EXPECTED"
  | "ACTUAL_OUTCOME"
  | "CONFIRMED"
  | "MISSED"
  | "INCOMPLETE"
  | "HUMAN_ADDED"
  | "MERIDIAN_ADDED"
  | "EFFECTIVE_ACTIONS"
  | "INEFFECTIVE_OR_UNNECESSARY_ACTIONS"
  | "SURPRISES"
  | "POSSIBLE_IMPROVEMENTS";

export interface ReflectionItem {
  item_id: string;
  surface: ReflectionSurface;
  statement: string;
  origin: string;
  evidence_refs: string[];
}

/**
 * Reflective evidence only. app/mel/models.py forces
 * operational_authority = False in model_post_init — this is a backend
 * invariant, not a UI convention. Never render a reflection as if it
 * decided anything.
 */
export interface ExperienceReflection {
  reflection_id: string;
  episode_id: string;
  run_id: string;
  episode_fingerprint: string;
  domain_view_version_used: string;
  domain_view_fingerprint_used: string;
  created_at: string;
  known_at_decision_time: ReflectionItem[];
  observed: ReflectionItem[];
  determined: ReflectionItem[];
  believed: ReflectionItem[];
  allowed: ReflectionItem[];
  unknown: ReflectionItem[];
  expected: ReflectionItem[];
  actual_outcome: ReflectionItem[];
  confirmed: ReflectionItem[];
  missed: ReflectionItem[];
  incomplete: ReflectionItem[];
  human_added: ReflectionItem[];
  meridian_added: ReflectionItem[];
  effective_actions: ReflectionItem[];
  ineffective_or_unnecessary_actions: ReflectionItem[];
  surprises: ReflectionItem[];
  possible_improvements: ReflectionItem[];
  generalization_risk: string;
  reflection_summary: string;
  content_fingerprint: string;
  operational_authority: false;
  reflection_role: ReflectionRole;
}

export interface ExperienceEpisode {
  episode_id: string;
  run_id: string;
  episode_started_at: string;
  episode_closed_at: string;
  terminal_outcome: EpisodeTerminalOutcome;
  domain_view_version: string;
  domain_view_fingerprint: string;
  content_fingerprint: string;
  summary: Record<string, unknown>;
  learning_eligible: boolean;
  holdout: boolean;
  dataset_role: DatasetRole | null;
  reflection_id: string | null;
}

export type LearningReceiptEnum =
  | "EXPERIENCE_LEARNED"
  | "EXPERIENCE_APPLIED"
  | "MEL_EVALUATION_FAILED"
  | "NO_SAFE_PROMOTABLE_LESSON"
  | "NO_MATCHING_HOLDOUT_APPLICATION"
  | "APPLICATION_FAILED"
  | "NOT_APPLICABLE"
  | "REJECTED_HOLDOUT_INPUT";

/**
 * Note: values are lowercase snake_case — this StrEnum's members serialize
 * to lowercase strings, unlike every other enum in this codebase. Do not
 * "fix" the casing to match the member names.
 */
export type LessonType =
  | "remediation_pattern"
  | "eda_routing"
  | "eda_interpretation_pattern"
  | "modeler_handoff_pattern"
  | "precheck_coverage_pattern"
  | "pre_modeling_failure_pattern"
  | "tool_efficacy"
  | "provider_schema_pattern"
  | "semantic_question_routing"
  | "response_prioritization_pattern";

/**
 * The regression guardrails a promotion must pass. model_ready_stable and
 * meridian_origin_stable are the receipt-level proof that promoting this
 * lesson did not violate the two non-negotiable truth-preservation rules
 * (frontend never computes MODEL_READY; official Meridian findings stay
 * separate from PreM3 interpretation).
 */
export interface RegressionResult {
  passed: boolean;
  matching_case_changed: boolean | null;
  non_matching_case_stable: boolean | null;
  model_ready_stable: boolean;
  meridian_origin_stable: boolean;
  numeric_diagnostics_stable: boolean;
  detail: string;
}

export interface PromotionReceipt {
  candidate_lesson_id: string;
  source_episode_ids: string[];
  evaluation_id: string;
  old_domain_view_version: string;
  old_domain_view_fingerprint: string;
  new_domain_view_version: string;
  new_domain_view_fingerprint: string;
  promoted_claim_id: string;
  lesson_type: LessonType;
  scope: ClaimScope;
  authority: LearnedAuthority;
  behavior_effect: string;
  regression_result: RegressionResult;
  promotion_timestamp: string;
  receipt_type: LearningReceiptEnum;
}

export interface ExperienceApplication {
  application_id: string;
  lesson_id: string;
  domain_view_claim_id: string;
  source_learning_episode_ids: string[];
  target_episode_id: string;
  domain_view_version: string;
  applicability_match: boolean;
  retrieved: boolean;
  retrieved_claim_ids: string[];
  retrieval_reason: string | null;
  behavior_before: Record<string, unknown>;
  behavior_after: Record<string, unknown>;
  expected_behavior_change: string;
  observed_behavior_change: string | null;
  validation_result: string;
  regression_result: string;
  created_at: string;
  receipt_type: LearningReceiptEnum | null;
}

/**
 * Frontend composition type binding an episode/reflection pair with the
 * two StructuredResponse payloads (LEARNING, DOMAIN_VIEW) the learning
 * section of a run workspace renders. `promotionReceipt` and
 * `application` are null until MEL actually proves EXPERIENCE_LEARNED /
 * EXPERIENCE_APPLIED for a given run — never populated speculatively.
 */
export interface ExperienceBundle {
  episode: ExperienceEpisode;
  reflection: ExperienceReflection | null;
  promotionReceipt: PromotionReceipt | null;
  application: ExperienceApplication | null;
}
