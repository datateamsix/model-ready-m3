import { beforeEach, describe, expect, it } from "vitest";
import { clearPlannerState, loadPlannerState, savePlannerState } from "./storage";
import { EMPTY_PLANNER_INTAKE } from "./types";
import { PLANNER_MANIFEST_VERSION } from "./manifest";

describe("Planner local storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("round-trips an intake with no result yet", () => {
    savePlannerState({ ...EMPTY_PLANNER_INTAKE, primaryOutcome: "Revenue" }, null);

    const loaded = loadPlannerState();

    expect(loaded?.intake.primaryOutcome).toBe("Revenue");
    expect(loaded?.result).toBeNull();
  });

  it("returns null when nothing has been stored yet", () => {
    expect(loadPlannerState()).toBeNull();
  });

  it("discards a draft stored under a different manifest version rather than reusing stale content", () => {
    window.localStorage.setItem(
      "prem3.planner.draft.v1",
      JSON.stringify({
        manifestVersion: "some-old-version",
        storedAt: new Date().toISOString(),
        intake: EMPTY_PLANNER_INTAKE,
        result: null,
      }),
    );

    expect(loadPlannerState()).toBeNull();
    // Reading a stale draft also clears it.
    expect(window.localStorage.getItem("prem3.planner.draft.v1")).toBeNull();
  });

  it("expires a draft older than 14 days", () => {
    const fifteenDaysAgo = new Date(Date.now() - 15 * 24 * 60 * 60 * 1000);
    window.localStorage.setItem(
      "prem3.planner.draft.v1",
      JSON.stringify({
        manifestVersion: PLANNER_MANIFEST_VERSION,
        storedAt: fifteenDaysAgo.toISOString(),
        intake: EMPTY_PLANNER_INTAKE,
        result: null,
      }),
    );

    expect(loadPlannerState(new Date())).toBeNull();
  });

  it("keeps a draft that is within the expiration window", () => {
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    window.localStorage.setItem(
      "prem3.planner.draft.v1",
      JSON.stringify({
        manifestVersion: PLANNER_MANIFEST_VERSION,
        storedAt: oneDayAgo.toISOString(),
        intake: { ...EMPTY_PLANNER_INTAKE, primaryOutcome: "Signups" },
        result: null,
      }),
    );

    expect(loadPlannerState(new Date())?.intake.primaryOutcome).toBe("Signups");
  });

  it("clears the stored draft", () => {
    savePlannerState(EMPTY_PLANNER_INTAKE, null);
    clearPlannerState();
    expect(loadPlannerState()).toBeNull();
  });
});
