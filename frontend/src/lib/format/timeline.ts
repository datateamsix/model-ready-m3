import { RUN_STAGE_ORDER, type RunStage } from "@/types/run";

export type RunStageStatus = "NOT_STARTED" | "ACTIVE" | "COMPLETE" | "FAILED";

export interface StageStatusEntry {
  stage: RunStage;
  status: RunStageStatus;
}

/**
 * Stages that branch off the golden path (RUN_STAGE_ORDER) but still have a
 * deterministic position within it, per app/core/state.py's real
 * _LEGAL_TRANSITIONS graph:
 *   ASSESSING -> WAITING_FOR_APPROVAL -> REMEDIATING | FAILED
 *   MODEL_READY -> WAITING_FOR_MODEL_APPROVAL -> MODELING -> LEARNING | COMPLETE | FAILED
 * Each maps to the last golden-path stage that must already be COMPLETE for
 * a run to be sitting in that branch stage. FAILED is deliberately not
 * mapped here: it is legally reachable from every stage, so a bare
 * `stage: "FAILED"` carries no positional information on its own -- callers
 * should pass the stage the run actually failed at plus `failed: true`
 * instead, which this function already handles correctly on its own.
 */
const BRANCH_STAGE_ANCHOR: Partial<Record<RunStage, RunStage>> = {
  WAITING_FOR_APPROVAL: "ASSESSING",
  WAITING_FOR_MODEL_APPROVAL: "MODEL_READY",
  MODELING: "MODEL_READY",
};

/**
 * Presentation-only: places the run's already-known `stage` value on the
 * golden-path ordering to decide which stages read as done/current/pending.
 * It never infers what stage a run is in — that comes from the backend.
 *
 * `currentStage` is not always a member of RUN_STAGE_ORDER — RunStage
 * includes real branch/waiting states (WAITING_FOR_APPROVAL,
 * WAITING_FOR_MODEL_APPROVAL, MODELING) that sit off the golden path.
 * Resolving those through BRANCH_STAGE_ANCHOR to the golden-path stage they
 * occur after means the stages that really did already complete still
 * render as COMPLETE, instead of every stage collapsing to NOT_STARTED.
 */
export function computeStageStatuses(
  currentStage: RunStage,
  failed: boolean,
): StageStatusEntry[] {
  const onGoldenPath = RUN_STAGE_ORDER.includes(currentStage);
  const anchorStage = onGoldenPath ? currentStage : BRANCH_STAGE_ANCHOR[currentStage];
  const currentIndex = anchorStage ? RUN_STAGE_ORDER.indexOf(anchorStage) : -1;
  // Only true when currentStage itself sits on the golden path. A resolved
  // branch stage has already moved past its anchor, so the anchor reads as
  // COMPLETE — it is not itself where the run is active or failed.
  const currentIsGoldenPathStage = onGoldenPath;

  return RUN_STAGE_ORDER.map((stage, index) => {
    if (currentIndex === -1) {
      return { stage, status: "NOT_STARTED" as const };
    }
    if (index < currentIndex) {
      return { stage, status: "COMPLETE" as const };
    }
    if (index === currentIndex) {
      if (!currentIsGoldenPathStage) {
        return { stage, status: "COMPLETE" as const };
      }
      return { stage, status: failed ? ("FAILED" as const) : ("COMPLETE" as const) };
    }
    return { stage, status: "NOT_STARTED" as const };
  }).map((entry, index) => {
    // The current stage itself is ACTIVE unless the run already reached a
    // terminal stage (COMPLETE) or failed at this stage.
    if (index === currentIndex && currentIsGoldenPathStage && currentStage !== "COMPLETE" && !failed) {
      return { stage: entry.stage, status: "ACTIVE" as const };
    }
    return entry;
  });
}
