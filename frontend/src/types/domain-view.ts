/**
 * Mirrors app/domain/intelligence/models.py. Hand-verified field-for-field
 * against the Python source and the real checked-in
 * app/domain/intelligence/data/current/domain_view.json (DOMAIN_VIEW v1).
 */

export type KnowledgeLayer =
  | "MERIDIAN_NORMATIVE"
  | "PREM3_POLICY"
  | "VERIFIED_DOMAIN_GUIDANCE"
  | "VALIDATED_EXPERIENCE_PATTERN"
  | "ADVISORY_LEARNED_PATTERN"
  | "OBSERVATION";

export type DomainViewKnowledgeClass =
  | "MERIDIAN_NORMATIVE"
  | "PREM3_POLICY"
  | "PREM3_POLICY_BLOCKER"
  | "PREM3_DETERMINISTIC_DIAGNOSTIC"
  | "MMM_EVIDENCE_HEURISTIC"
  | "MMM_JUDGMENT"
  | "DESIGN_DEFAULT"
  | "VALIDATED_EXPERIENCE_PATTERN"
  | "ADVISORY_LEARNED_PATTERN"
  | "OBSERVATION";

export type LearnedAuthority =
  | "OBSERVATION_ONLY"
  | "ADVISORY"
  | "ROUTING_HINT"
  | "AUTO_SAFE_POLICY"
  | "NONE";

export type SourceType =
  | "OFFICIAL_SOURCE"
  | "PREM3_POLICY"
  | "FOUNDATIONAL_EVIDENCE"
  | "CROSS_FRAMEWORK_EVIDENCE"
  | "PROMOTED_EXPERIENCE";

export type ScopeLevel =
  | "GLOBAL"
  | "ORGANIZATION"
  | "WORKSPACE"
  | "PROVIDER"
  | "REPORT_TYPE"
  | "SCHEMA_PATTERN"
  | "VARIABLE_CLASS"
  | "CHANNEL_TYPE"
  | "MODEL_TYPE"
  | "RUN";

export type ClaimStatus = "ACTIVE" | "SUPERSEDED" | "REVOKED" | "REJECTED";

export interface ClaimScope {
  level: ScopeLevel;
  value: string | null;
}

/**
 * Present (possibly null) on every real DOMAIN_VIEW claim, including in
 * the checked-in v1.0.0 data. The actual proof backing a
 * VALIDATED_EXPERIENCE_PATTERN / ADVISORY_LEARNED_PATTERN claim — which
 * episodes taught it, what evidence supported it, which promotion receipt
 * sealed it. A claim with experience_provenance: null is not a learned
 * pattern; never render one as if it were.
 */
export interface ExperienceProvenance {
  candidate_lesson_id: string | null;
  episode_ids: string[];
  evaluation_evidence: string[];
  regression_evidence: string[];
  promotion_receipt_id: string | null;
  promotion_timestamp: string | null;
}

export interface DomainViewClaim {
  claim_id: string;
  statement: string;
  knowledge_class: DomainViewKnowledgeClass;
  layer: KnowledgeLayer;
  authority: LearnedAuthority;
  scope: ClaimScope;
  source_type: SourceType;
  source_refs: string[];
  source_version: string | null;
  evidence: string[];
  regression_status: string;
  behavior_effect: string | null;
  first_added_at: string | null;
  last_validated_at: string | null;
  supersedes: string | null;
  superseded_by: string | null;
  status: ClaimStatus;
  prohibited_overrides: string[];
  experience_provenance: ExperienceProvenance | null;
}

export interface DomainViewSourceVersions {
  intelligence_version: string;
  product_context_version: string;
  mmm_boot_context_version: string;
  rule_registry_version: string;
  intelligence_registry_version: string;
  source_verification_date: string;
  meridian_worker_pin: string;
}

export interface DomainView {
  domain_view_version: string;
  generated_at: string;
  source_versions: DomainViewSourceVersions;
  promoted_lesson_set_version: string;
  promoted_lesson_count: number;
  content_fingerprint: string;
  previous_domain_view_version: string | null;
  status: string;
  claims: DomainViewClaim[];
}

export type ChangeType =
  | "INITIAL_COMPILE"
  | "OFFICIAL_SOURCE_UPDATE"
  | "POLICY_UPDATE"
  | "HEURISTIC_UPDATE"
  | "EXPERIENCE_LEARNED"
  | "LESSON_AUTHORITY_CHANGE"
  | "LESSON_SCOPE_CHANGE"
  | "LESSON_REVOKED"
  | "LESSON_SUPERSEDED";

/**
 * Mirrors app/domain/intelligence/models.py's DomainViewDiff. No real diff
 * exists yet (DOMAIN_VIEW is still v1.0.0 with 0 promoted lessons) — this
 * type exists so DomainViewDiff (Task 23) has a real shape to accept
 * instead of inventing one once a v1 -> v2 diff is ever produced.
 */
export interface DomainViewDiff {
  added_claim_ids: string[];
  removed_claim_ids: string[];
  modified_claim_ids: string[];
  authority_changes: Record<string, unknown>[];
  scope_changes: Record<string, unknown>[];
  source_updates: string[];
  experiential_learning_changes: string[];
  change_types: ChangeType[];
}
