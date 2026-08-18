import { describe, expect, it, vi } from "vitest";

const mockCallPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/server/prem3-api-client")>(
    "@/lib/server/prem3-api-client",
  );
  return { ...actual, callPreM3Api: (...args: unknown[]) => mockCallPreM3Api(...args) };
});

import { ApiPlanSource } from "./api-plan-source";

const PLAN_RESPONSE = {
  planning_run_id: "p-1",
  workspace_id: "w-1",
  objective: "Understand paid social contribution to signups",
  recommended_sources: ["Meta Ads export", "Google Ads export"],
  provider_export_requirements: ["Daily spend by campaign"],
  fields_to_collect: ["spend", "impressions"],
  history_grain_guidance: "At least 52 weeks of weekly data",
  controls_confounders: ["Seasonality", "Promotions"],
  known_gaps: ["No offline conversion data"],
  owner_label: "PreM3 (autonomous)",
  next_actions: ["Connect Meta Ads export"],
  provenance_label: "Generated from onboarding intake",
  plan_version: "1",
  generated_at: "Aug 1, 2026",
};

describe("ApiPlanSource", () => {
  it("fetches a plan from the assumed /v1/workspaces/{id}/plans/{id} endpoint, mapped to AcquisitionPlanDetail", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: PLAN_RESPONSE });
    const source = new ApiPlanSource();

    const result = await source.getPlan("w-1", "p-1");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/workspaces/w-1/plans/p-1");
    expect(result).toEqual({
      ok: true,
      data: {
        planningRunId: "p-1",
        workspaceId: "w-1",
        objective: "Understand paid social contribution to signups",
        recommendedSources: ["Meta Ads export", "Google Ads export"],
        providerExportRequirements: ["Daily spend by campaign"],
        fieldsToCollect: ["spend", "impressions"],
        historyGrainGuidance: "At least 52 weeks of weekly data",
        controlsConfounders: ["Seasonality", "Promotions"],
        knownGaps: ["No offline conversion data"],
        ownerLabel: "PreM3 (autonomous)",
        nextActions: ["Connect Meta Ads export"],
        provenanceLabel: "Generated from onboarding intake",
        planVersion: "1",
        generatedAtLabel: "Aug 1, 2026",
      },
    });
  });

  it("passes a typed error straight through without inventing a fallback plan", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiPlanSource();

    const result = await source.getPlan("w-1", "p-1");

    expect(result.ok).toBe(false);
  });
});
