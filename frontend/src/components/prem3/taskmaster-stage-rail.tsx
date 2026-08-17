import { cn } from "@/lib/utils";
import { StatusBadge } from "./status-badge";
import type { TaskmasterStage } from "@/types/ui/taskmaster";

/**
 * M2-13: unlike Mission 1's RunTimeline (@/components/prem3/run-timeline.tsx,
 * @/lib/format/timeline.ts's computeStageStatuses), this never derives a
 * stage's status from a single `currentStage` enum -- every stage's status
 * comes straight off the backend read model. `currentStageId` only controls
 * which row gets visual emphasis; it never changes what status renders.
 */
export function TaskmasterStageRail({
  stages,
  currentStageId,
}: {
  stages: TaskmasterStage[];
  currentStageId: string | null;
}) {
  return (
    <ol className="flex flex-col gap-2 rounded-lg border border-prem3-cool-gray bg-white p-2">
      {stages.map((stage) => {
        const isCurrent = stage.stageId === currentStageId;
        return (
          <li
            key={stage.stageId}
            data-testid={`taskmaster-stage-${stage.stageId}`}
            data-current={isCurrent}
            className={cn(
              "flex items-center justify-between gap-3 rounded-md px-3 py-2",
              isCurrent && "bg-prem3-light-gray ring-1 ring-prem3-indigo",
            )}
          >
            <div className="flex items-center gap-2">
              <span className={cn("text-sm", isCurrent ? "font-semibold text-prem3-navy" : "text-prem3-navy/80")}>
                {stage.label}
              </span>
              {stage.requiresApproval && (
                <span className="rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-800">
                  Approval required
                </span>
              )}
            </div>
            <StatusBadge status={stage.status} />
          </li>
        );
      })}
    </ol>
  );
}
