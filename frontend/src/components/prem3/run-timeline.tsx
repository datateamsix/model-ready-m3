import { Check, CircleX, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { computeStageStatuses, type RunStageStatus } from "@/lib/format/timeline";
import type { RunStage } from "@/types/run";

const STAGE_LABEL: Record<RunStage, string> = {
  NEW: "New",
  DISCOVERING: "Map",
  PROFILING: "Profile",
  MAPPING: "Mend",
  ASSESSING: "Assess",
  WAITING_FOR_APPROVAL: "Awaiting approval",
  REMEDIATING: "Remediate",
  VALIDATING: "Validate",
  PUBLISHING: "Publish",
  EXPLORING: "Explore",
  MODEL_READY: "Model ready",
  WAITING_FOR_MODEL_APPROVAL: "Awaiting model approval",
  MODELING: "Model fit",
  FAILED: "Failed",
  LEARNING: "Learn",
  COMPLETE: "Complete",
};

const DOT_CLASSES: Record<RunStageStatus, string> = {
  NOT_STARTED: "border-prem3-cool-gray bg-white text-prem3-navy/30",
  ACTIVE: "border-prem3-indigo bg-prem3-indigo text-white",
  COMPLETE: "border-prem3-indigo bg-white text-prem3-indigo",
  FAILED: "border-red-600 bg-red-600 text-white",
};

function StageIcon({ status }: { status: RunStageStatus }) {
  if (status === "COMPLETE") return <Check className="size-3.5" aria-hidden="true" />;
  if (status === "ACTIVE") return <Loader2 className="size-3.5 animate-spin motion-reduce:animate-none" aria-hidden="true" />;
  if (status === "FAILED") return <CircleX className="size-3.5" aria-hidden="true" />;
  return null;
}

export function RunTimeline({ currentStage, failed }: { currentStage: RunStage; failed: boolean }) {
  const statuses = computeStageStatuses(currentStage, failed);

  return (
    <ol className="flex flex-wrap items-center gap-x-1 gap-y-3">
      {statuses.map(({ stage, status }, index) => (
        <li key={stage} className="flex items-center">
          <div
            data-testid={`stage-${stage}`}
            data-status={status}
            className="flex flex-col items-center gap-1.5"
          >
            <span
              className={cn(
                "flex size-6 items-center justify-center rounded-full border-2",
                DOT_CLASSES[status],
              )}
            >
              <StageIcon status={status} />
            </span>
            <span className="text-[11px] font-medium text-prem3-navy/70">{STAGE_LABEL[stage]}</span>
          </div>
          {index < statuses.length - 1 && (
            <span className="mx-2 h-px w-6 shrink-0 bg-prem3-cool-gray sm:w-10" aria-hidden="true" />
          )}
        </li>
      ))}
    </ol>
  );
}
