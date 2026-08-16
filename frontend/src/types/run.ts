/**
 * Mirrors app/core/state.py (RunStage) and app/core/contracts.py.
 * Hand-verified field-for-field against the Python source.
 */

export type RunStage =
  | "NEW"
  | "DISCOVERING"
  | "PROFILING"
  | "MAPPING"
  | "ASSESSING"
  | "WAITING_FOR_APPROVAL"
  | "REMEDIATING"
  | "VALIDATING"
  | "PUBLISHING"
  | "EXPLORING"
  | "MODEL_READY"
  | "WAITING_FOR_MODEL_APPROVAL"
  | "MODELING"
  | "FAILED"
  | "LEARNING"
  | "COMPLETE";

/** The default golden-path ordering used to render the run timeline. */
export const RUN_STAGE_ORDER: RunStage[] = [
  "NEW",
  "DISCOVERING",
  "PROFILING",
  "MAPPING",
  "ASSESSING",
  "REMEDIATING",
  "VALIDATING",
  "PUBLISHING",
  "EXPLORING",
  "MODEL_READY",
  "LEARNING",
  "COMPLETE",
];

export const TERMINAL_STAGES: ReadonlySet<RunStage> = new Set(["FAILED", "COMPLETE"]);

export type Severity = "INFO" | "WARN" | "ERROR";
export type RemediationClass = "AUTO_SAFE" | "APPROVAL_REQUIRED" | "BLOCKED";
export type ActionStatus = "PROPOSED" | "APPLIED" | "REJECTED" | "FAILED";
export type IssueStatus = "OPEN" | "REMEDIATING" | "RESOLVED";

export interface RunStatusEvent {
  run_id: string;
  stage: RunStage;
  status: string;
  message: string;
  timestamp: string;
  progress: number;
}

export interface Issue {
  issue_id: string;
  rule_id: string;
  severity: Severity;
  title: string;
  evidence: Record<string, unknown>;
  remediation_class: RemediationClass;
  proposed_action: Record<string, unknown>;
  status: IssueStatus;
  resolution_action_ids: string[];
  resolved_at: string | null;
  resolution_evidence: Record<string, unknown>;
}

export interface Transformation {
  action_id: string;
  tool: string;
  source_fields: string[];
  target_fields: string[];
  parameters: Record<string, unknown>;
  reason: string;
  lesson_ids: string[];
  status: ActionStatus;
}

export interface ParityCheck {
  name: string;
  passed: boolean;
  evidence: Record<string, unknown>;
}

export interface BigQueryPublishReceipt {
  run_id: string;
  status: string;
  project_id: string;
  dataset_id: string;
  table_id: string;
  view_id: string | null;
  row_count: number;
  schema_fingerprint: string;
  artifact_fingerprint: string;
  published_fingerprint: string;
  parity_status: string;
  meridian_contract_uri: string;
  provenance_uri: string;
  parity_checks: ParityCheck[];
  physical_schema_fingerprint: string;
  partition_field: string | null;
  clustering_fields: string[];
  consumption_view: string;
  model_ready_manifest_uri: string;
}

export type LearningReceiptType = "EXPERIENCE_LEARNED" | "EXPERIENCE_APPLIED";

export interface LearningReceipt {
  receipt_id: string;
  receipt_type: LearningReceiptType;
  run_id: string;
  lesson_id: string;
  evidence: string[];
  confidence: number;
  risk: string;
  measured_change: Record<string, unknown>;
  validation_status: string;
}

/**
 * Frontend-only composition type for run lists/headers. Not a 1:1 mirror of
 * any single Python model — assembled from DurableRunState-shaped fields
 * that already exist on the backend (run_id, stage, issue counts, business
 * identity) for display purposes only. Never used to compute readiness.
 */
export interface RunSummary {
  run_id: string;
  business: string;
  dataset_label: string;
  stage: RunStage;
  failed: boolean;
  created_at: string;
  updated_at: string;
  detected_issue_count: number;
  resolved_issue_count: number;
  open_issue_count: number;
  geos: string[];
  grain: string;
  period_count: number;
}
