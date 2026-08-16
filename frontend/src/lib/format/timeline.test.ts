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
});
