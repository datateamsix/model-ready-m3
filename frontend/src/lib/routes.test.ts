import { describe, expect, it } from "vitest";
import { routes } from "./routes";

describe("routes", () => {
  it("builds every public marketing and auth path exactly as specified in the Mission 2 IA", () => {
    expect(routes.home()).toBe("/");
    expect(routes.howItWorks()).toBe("/how-it-works");
    expect(routes.pricing()).toBe("/pricing");
    expect(routes.planner()).toBe("/planner");
    expect(routes.start()).toBe("/start");
    expect(routes.signIn()).toBe("/sign-in");
    expect(routes.signUp()).toBe("/sign-up");
    expect(routes.privacy()).toBe("/privacy");
    expect(routes.terms()).toBe("/terms");
  });

  it("builds the public demo run path under /app/demo, not the legacy /runs path", () => {
    expect(routes.publicDemoRun("music-center-dataset-a-demo")).toBe(
      "/app/demo/runs/music-center-dataset-a-demo",
    );
  });

  it("builds every authenticated workspace path with the internal workspaceId, nested correctly", () => {
    expect(routes.app()).toBe("/app");
    expect(routes.workspace("ws-1")).toBe("/app/w/ws-1");
    expect(routes.workspacePlans("ws-1")).toBe("/app/w/ws-1/plans");
    expect(routes.workspacePlan("ws-1", "plan-1")).toBe("/app/w/ws-1/plans/plan-1");
    expect(routes.workspaceDatasets("ws-1")).toBe("/app/w/ws-1/datasets");
    expect(routes.workspaceDataset("ws-1", "ds-1")).toBe("/app/w/ws-1/datasets/ds-1");
    expect(routes.workspaceDatasetRun("ws-1", "ds-1", "run-1")).toBe(
      "/app/w/ws-1/datasets/ds-1/runs/run-1",
    );
    expect(routes.workspaceTaskmaster("ws-1")).toBe("/app/w/ws-1/taskmaster");
    expect(routes.settingsAccount()).toBe("/app/settings/account");
    expect(routes.settingsBilling()).toBe("/app/settings/billing");
  });
});
