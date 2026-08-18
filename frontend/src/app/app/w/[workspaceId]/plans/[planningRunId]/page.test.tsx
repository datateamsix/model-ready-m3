import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockGetPlan = vi.fn();
vi.mock("@/lib/adapters/api-plan-source", () => ({
  planSource: { getPlan: (...args: unknown[]) => mockGetPlan(...args) },
}));

import Page from "./page";

function params(workspaceId: string, planningRunId: string) {
  return { params: Promise.resolve({ workspaceId, planningRunId }) };
}

const REAL_PLAN = {
  planningRunId: "p-1",
  workspaceId: "w-1",
  objective: "Understand paid social contribution to signups",
  recommendedSources: ["Meta Ads export"],
  providerExportRequirements: ["Daily spend by campaign"],
  fieldsToCollect: ["spend"],
  historyGrainGuidance: null,
  controlsConfounders: [],
  knownGaps: [],
  ownerLabel: null,
  nextActions: ["Connect Meta Ads export"],
  provenanceLabel: "Generated from onboarding intake",
  planVersion: "1",
  generatedAtLabel: "Aug 1, 2026",
};

describe("/app/w/[workspaceId]/plans/[planningRunId]", () => {
  it("renders an honest 'not connected yet' state when REQ-010 is unconfigured (503)", async () => {
    mockGetPlan.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });

    render(await Page(params("w-1", "p-1")));

    expect(screen.getByText("This plan isn't connected yet")).toBeInTheDocument();
  });

  it("scopes the lookup to both the workspace and planning run from the route", async () => {
    mockGetPlan.mockResolvedValue({ ok: true, data: REAL_PLAN });

    render(await Page(params("w-42", "p-9")));

    expect(mockGetPlan).toHaveBeenCalledWith("w-42", "p-9");
  });

  it("renders the plan as an actionable artifact with real objective/sources/actions, never fabricated", async () => {
    mockGetPlan.mockResolvedValue({ ok: true, data: REAL_PLAN });

    render(await Page(params("w-1", "p-1")));

    expect(screen.getByText("Understand paid social contribution to signups")).toBeInTheDocument();
    expect(screen.getByText("Meta Ads export")).toBeInTheDocument();
    expect(screen.getByText("Connect Meta Ads export")).toBeInTheDocument();
    expect(screen.getByText(/Plan v1/)).toBeInTheDocument();
  });

  it("shows honest fallbacks for null/empty sections instead of inventing content", async () => {
    mockGetPlan.mockResolvedValue({ ok: true, data: REAL_PLAN });

    render(await Page(params("w-1", "p-1")));

    expect(screen.getByText("Not yet assigned.")).toBeInTheDocument();
    expect(screen.getAllByText("None.").length).toBeGreaterThan(0);
  });
});
