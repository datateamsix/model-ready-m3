import Link from "next/link";
import { StatusBadge } from "./status-badge";
import { routes } from "@/lib/routes";
import type { EvaluationHistoryEntry } from "@/types/ui/commercial";

/**
 * One row per evaluation run under a Dataset -- visibly distinct from
 * DatasetSummaryRow (a different component, a different link target: a
 * specific run, not the dataset). No run-quota UI: this only ever lists
 * evaluations that actually happened.
 */
export function EvaluationHistoryRow({
  evaluation,
  workspaceId,
  datasetId,
}: {
  evaluation: EvaluationHistoryEntry;
  workspaceId: string;
  datasetId: string;
}) {
  return (
    <Link
      href={routes.workspaceDatasetRun(workspaceId, datasetId, evaluation.runId)}
      className="flex items-center justify-between gap-3 border-b border-prem3-cool-gray py-2.5 last:border-b-0"
    >
      <span className="text-sm text-prem3-navy">{evaluation.evaluatedAtLabel}</span>
      <StatusBadge status={evaluation.status} />
    </Link>
  );
}
