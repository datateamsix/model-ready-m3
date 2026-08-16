/**
 * Mirrors app/intelligence/contracts.py. Hand-verified field-for-field
 * against the Python source — do not add or rename members without
 * re-checking the backend file.
 */

export type KnowledgeClass =
  | "MERIDIAN_NORMATIVE"
  | "PREM3_DETERMINISTIC_DIAGNOSTIC"
  | "MMM_EVIDENCE_HEURISTIC"
  | "MMM_JUDGMENT"
  | "PREM3_POLICY_BLOCKER"
  | "DOMAIN_VIEW_LEARNED";

export type DecisionClass =
  | "AUTO_BLOCK"
  | "AUTO_SAFE"
  | "ADVISORY"
  | "APPROVAL_REQUIRED"
  | "MODELER_REVIEW_REQUIRED"
  | "USER_REQUIRED";

export type ResponsibleActor =
  | "PREM3"
  | "MARKETER"
  | "ANALYST"
  | "DATA_ENGINEER"
  | "MODELER"
  | "SYSTEM_ADMIN";

export const KNOWLEDGE_AUTHORITY_LABELS: Record<KnowledgeClass, string> = {
  MERIDIAN_NORMATIVE: "Official Meridian requirement",
  PREM3_DETERMINISTIC_DIAGNOSTIC: "PreM3 deterministic diagnostic",
  MMM_EVIDENCE_HEURISTIC: "MMM best-practice heuristic",
  MMM_JUDGMENT: "Modeler judgment",
  PREM3_POLICY_BLOCKER: "PreM3 policy blocker",
  DOMAIN_VIEW_LEARNED: "DOMAIN_VIEW learned pattern",
};
