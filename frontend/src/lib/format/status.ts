import type { PresentationStatus } from "@/types/response";

export type StatusTone = "positive" | "warning" | "critical" | "pending" | "neutral";

const TONE_BY_STATUS: Record<PresentationStatus, StatusTone> = {
  PASS: "positive",
  READY: "positive",
  COMPLETE: "positive",
  REVIEW_RECOMMENDED: "warning",
  MODELER_REVIEW_REQUIRED: "warning",
  USER_ACTION_REQUIRED: "critical",
  BLOCKED: "critical",
  PENDING: "pending",
  NOT_APPLICABLE: "neutral",
};

export function statusTone(status: PresentationStatus): StatusTone {
  return TONE_BY_STATUS[status];
}

export const STATUS_LABEL: Record<PresentationStatus, string> = {
  PASS: "Pass",
  READY: "Ready",
  REVIEW_RECOMMENDED: "Review recommended",
  USER_ACTION_REQUIRED: "User action required",
  MODELER_REVIEW_REQUIRED: "Modeler review required",
  BLOCKED: "Blocked",
  PENDING: "Pending",
  NOT_APPLICABLE: "Not applicable",
  COMPLETE: "Complete",
};

export function severityTone(severity: "ERROR" | "ATTENTION" | "INFO"): StatusTone {
  if (severity === "ERROR") return "critical";
  if (severity === "ATTENTION") return "warning";
  return "neutral";
}
