import Link from "next/link";
import { FlaskConical } from "lucide-react";
import { StatusBadge } from "./status-badge";
import { routes } from "@/lib/routes";
import type { DatasetSummary } from "@/types/ui/commercial";

/**
 * Links to the Dataset, not into a specific run -- dataset and run are
 * visibly distinct objects (M2-03's acceptance criterion). evaluationCount
 * is rendered as a plain real count, never "X of Y" -- re-evaluations are
 * unlimited on every paid plan, so there is no cap to imply.
 */
export function DatasetSummaryRow({
  dataset,
  workspaceId,
}: {
  dataset: DatasetSummary;
  workspaceId: string;
}) {
  return (
    <Link
      href={routes.workspaceDataset(workspaceId, dataset.datasetId)}
      className="flex items-center justify-between gap-3 rounded-lg border border-prem3-cool-gray bg-white px-4 py-3 transition-colors hover:border-prem3-indigo"
    >
      <div>
        <p className="text-sm font-medium text-prem3-navy">{dataset.name}</p>
        <p className="text-xs text-muted-foreground">
          {[dataset.kpiLabel, dataset.grainLabel].filter(Boolean).join(" · ") || "No KPI/grain set"}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <FlaskConical className="size-3" aria-hidden="true" />
          {dataset.evaluationCount} {dataset.evaluationCount === 1 ? "evaluation" : "evaluations"}
        </span>
        {dataset.latestEvaluationStatus && <StatusBadge status={dataset.latestEvaluationStatus} />}
      </div>
    </Link>
  );
}
