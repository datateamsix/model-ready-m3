import { RUN_STAGE_ORDER, type RunStage } from "@/types/run";

export type RunStageStatus = "NOT_STARTED" | "ACTIVE" | "COMPLETE" | "FAILED";

export interface StageStatusEntry {
  stage: RunStage;
  status: RunStageStatus;
}

/**
 * Presentation-only: places the run's already-known `stage` value on the
 * golden-path ordering to decide which stages read as done/current/pending.
 * It never infers what stage a run is in — that comes from the backend.
 */
export function computeStageStatuses(
  currentStage: RunStage,
  failed: boolean,
): StageStatusEntry[] {
  const currentIndex = RUN_STAGE_ORDER.indexOf(currentStage);

  return RUN_STAGE_ORDER.map((stage, index) => {
    if (currentIndex === -1) {
      return { stage, status: "NOT_STARTED" as const };
    }
    if (index < currentIndex) {
      return { stage, status: "COMPLETE" as const };
    }
    if (index === currentIndex) {
      return { stage, status: failed ? ("FAILED" as const) : ("COMPLETE" as const) };
    }
    return { stage, status: "NOT_STARTED" as const };
  }).map((entry, index) => {
    // The current stage itself is ACTIVE unless the run already reached a
    // terminal stage (COMPLETE) or failed at this stage.
    if (index === currentIndex && currentStage !== "COMPLETE" && !failed) {
      return { stage: entry.stage, status: "ACTIVE" as const };
    }
    return entry;
  });
}
