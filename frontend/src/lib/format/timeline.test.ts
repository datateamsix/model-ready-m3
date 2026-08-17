import { describe, expect, it } from "vitest";
import { computeStageStatuses } from "./timeline";

describe("computeStageStatuses", () => {
  it("marks every stage before the current one COMPLETE and the current one ACTIVE", () => {
    const statuses = computeStageStatuses("VALIDATING", false);
    const byStage = Object.fromEntries(statuses.map((s) => [s.stage, s.status]));
    expect(byStage.MAPPING).toBe("COMPLETE");
    expect(byStage.VALIDATING).toBe("ACTIVE");
    expect(byStage.PUBLISHING).toBe("NOT_STARTED");
  });

  it("marks a terminal MODEL_READY run's remaining stages COMPLETE, not ACTIVE", () => {
    const statuses = computeStageStatuses("COMPLETE", false);
    const byStage = Object.fromEntries(statuses.map((s) => [s.stage, s.status]));
    expect(byStage.MODEL_READY).toBe("COMPLETE");
    expect(byStage.COMPLETE).toBe("COMPLETE");
  });

  it("marks the current stage FAILED when the run failed, without inventing progress past it", () => {
    const statuses = computeStageStatuses("REMEDIATING", true);
    const byStage = Object.fromEntries(statuses.map((s) => [s.stage, s.status]));
    expect(byStage.REMEDIATING).toBe("FAILED");
    expect(byStage.VALIDATING).toBe("NOT_STARTED");
  });

  // RunStage has real branch/waiting states -- WAITING_FOR_APPROVAL,
  // WAITING_FOR_MODEL_APPROVAL, MODELING -- that app/core/state.py's legal
  // transition graph shows sitting off RUN_STAGE_ORDER's golden path
  // (ASSESSING -> WAITING_FOR_APPROVAL -> REMEDIATING | FAILED;
  // MODEL_READY -> WAITING_FOR_MODEL_APPROVAL -> MODELING -> LEARNING |
  // COMPLETE | FAILED). RUN_STAGE_ORDER.indexOf() returns -1 for all three,
  // which previously collapsed every golden-path stage to NOT_STARTED --
  // hiding real, already-completed progress whenever a run was waiting on a
  // human approval or fitting a model.
  it("marks ASSESSING complete (not every stage NOT_STARTED) while waiting for remediation approval", () => {
    const statuses = computeStageStatuses("WAITING_FOR_APPROVAL", false);
    const byStage = Object.fromEntries(statuses.map((s) => [s.stage, s.status]));
    expect(byStage.MAPPING).toBe("COMPLETE");
    expect(byStage.ASSESSING).toBe("COMPLETE");
    expect(byStage.REMEDIATING).toBe("NOT_STARTED");
    expect(byStage.VALIDATING).toBe("NOT_STARTED");
  });

  it("marks MODEL_READY complete while waiting for modeler approval to fit", () => {
    const statuses = computeStageStatuses("WAITING_FOR_MODEL_APPROVAL", false);
    const byStage = Object.fromEntries(statuses.map((s) => [s.stage, s.status]));
    expect(byStage.EXPLORING).toBe("COMPLETE");
    expect(byStage.MODEL_READY).toBe("COMPLETE");
    expect(byStage.LEARNING).toBe("NOT_STARTED");
  });

  it("marks MODEL_READY complete (not ACTIVE/FAILED) while the model is actively fitting", () => {
    const statuses = computeStageStatuses("MODELING", false);
    const byStage = Object.fromEntries(statuses.map((s) => [s.stage, s.status]));
    expect(byStage.MODEL_READY).toBe("COMPLETE");
    expect(byStage.LEARNING).toBe("NOT_STARTED");
  });

  it("does not mark a branch stage's anchor FAILED even when the run failed while waiting", () => {
    // The run completed ASSESSING, then failed during WAITING_FOR_APPROVAL
    // itself (not during ASSESSING) -- ASSESSING should still read COMPLETE.
    const statuses = computeStageStatuses("WAITING_FOR_APPROVAL", true);
    const byStage = Object.fromEntries(statuses.map((s) => [s.stage, s.status]));
    expect(byStage.ASSESSING).toBe("COMPLETE");
  });

  it("falls back to NOT_STARTED for every stage when given the literal FAILED stage with no known anchor", () => {
    // FAILED is legally reachable from every RunStage (app/core/state.py's
    // _LEGAL_TRANSITIONS), so a bare stage: "FAILED" carries no positional
    // information on its own -- callers should pass the stage the run
    // actually failed at plus failed: true instead (see the test above).
    // This is the one case with no honest COMPLETE to claim, so the
    // conservative NOT_STARTED fallback is intentional, not a bug.
    const statuses = computeStageStatuses("FAILED", false);
    expect(statuses.every((s) => s.status === "NOT_STARTED")).toBe(true);
  });
});
