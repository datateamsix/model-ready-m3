import { describe, expect, it } from "vitest";
import { RUN_STAGE_ORDER, TERMINAL_STAGES } from "./run";

describe("run stage contract", () => {
  it("orders MODEL_READY before LEARNING and COMPLETE", () => {
    const modelReadyIndex = RUN_STAGE_ORDER.indexOf("MODEL_READY");
    const learningIndex = RUN_STAGE_ORDER.indexOf("LEARNING");
    const completeIndex = RUN_STAGE_ORDER.indexOf("COMPLETE");
    expect(modelReadyIndex).toBeGreaterThan(-1);
    expect(modelReadyIndex).toBeLessThan(learningIndex);
    expect(learningIndex).toBeLessThan(completeIndex);
  });

  it("treats FAILED and COMPLETE as the only terminal stages", () => {
    expect(TERMINAL_STAGES.has("FAILED")).toBe(true);
    expect(TERMINAL_STAGES.has("COMPLETE")).toBe(true);
    expect(TERMINAL_STAGES.has("MODEL_READY")).toBe(false);
  });
});
