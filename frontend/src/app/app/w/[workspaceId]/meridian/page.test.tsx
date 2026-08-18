import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockGetMeridianIntegration = vi.fn();
vi.mock("@/lib/adapters/api-meridian-source", () => ({
  meridianSource: { getMeridianIntegration: (...args: unknown[]) => mockGetMeridianIntegration(...args) },
}));

import Page from "./page";

function params(workspaceId: string) {
  return { params: Promise.resolve({ workspaceId }) };
}

const REAL_SUMMARY = {
  workspaceId: "w-1",
  edaReportStatus: null,
  edaReportUrl: null,
  modelReadyDataLocationLabel: null,
  bigQueryPublishVerified: null,
  requiredArtifacts: [],
  integrationChecks: [],
  readinessReceiptLabel: null,
  nextApprovedModelingAction: null,
};

describe("/app/w/[workspaceId]/meridian", () => {
  it("renders an honest 'not connected yet' state when REQ-017 is unconfigured (503)", async () => {
    mockGetMeridianIntegration.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });

    render(await Page(params("w-1")));

    expect(screen.getByText("Meridian Integration isn't connected yet")).toBeInTheDocument();
  });

  it("scopes the lookup to the workspace from the route", async () => {
    mockGetMeridianIntegration.mockResolvedValue({ ok: true, data: REAL_SUMMARY });

    render(await Page(params("w-42")));

    expect(mockGetMeridianIntegration).toHaveBeenCalledWith("w-42");
  });

  it("shows honest 'not yet available' notes for every field, never a fabricated readiness claim", async () => {
    mockGetMeridianIntegration.mockResolvedValue({ ok: true, data: REAL_SUMMARY });

    render(await Page(params("w-1")));

    expect(screen.getAllByText("Not yet available.").length).toBeGreaterThan(0);
    expect(screen.queryByText("Verified.")).not.toBeInTheDocument();
  });

  it("renders real integration checks with their real status when the backend supplies them", async () => {
    mockGetMeridianIntegration.mockResolvedValue({
      ok: true,
      data: {
        ...REAL_SUMMARY,
        bigQueryPublishVerified: true,
        integrationChecks: [{ label: "Schema validated", status: "PASS" }],
      },
    });

    render(await Page(params("w-1")));

    expect(screen.getByText("Schema validated")).toBeInTheDocument();
    expect(screen.getByText("Verified.")).toBeInTheDocument();
  });
});
