import { describe, expect, it, vi } from "vitest";

const mockCallPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/server/prem3-api-client")>(
    "@/lib/server/prem3-api-client",
  );
  return { ...actual, callPreM3Api: (...args: unknown[]) => mockCallPreM3Api(...args) };
});

import { ApiMeridianSource } from "./api-meridian-source";

const MERIDIAN_RESPONSE = {
  workspace_id: "w-1",
  eda_report_status: "Complete",
  eda_report_url: "https://example.com/eda-report",
  model_ready_data_location_label: "BigQuery dataset prem3_mmm_ready",
  bigquery_publish_verified: true,
  required_artifacts: ["Model-ready table", "Field mapping"],
  integration_checks: [{ label: "Schema validated", status: "PASS" as const }],
  readiness_receipt_label: "Issued Aug 1, 2026",
  next_approved_modeling_action: "Hand off to Meridian modeling workflow",
};

describe("ApiMeridianSource", () => {
  it("fetches the Meridian Integration summary from the assumed endpoint", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: MERIDIAN_RESPONSE });
    const source = new ApiMeridianSource();

    const result = await source.getMeridianIntegration("w-1");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/workspaces/w-1/meridian-integration");
    expect(result).toEqual({
      ok: true,
      data: {
        workspaceId: "w-1",
        edaReportStatus: "Complete",
        edaReportUrl: "https://example.com/eda-report",
        modelReadyDataLocationLabel: "BigQuery dataset prem3_mmm_ready",
        bigQueryPublishVerified: true,
        requiredArtifacts: ["Model-ready table", "Field mapping"],
        integrationChecks: [{ label: "Schema validated", status: "PASS" }],
        readinessReceiptLabel: "Issued Aug 1, 2026",
        nextApprovedModelingAction: "Hand off to Meridian modeling workflow",
      },
    });
  });

  it("passes a typed error straight through without inventing a fallback readiness claim", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiMeridianSource();

    const result = await source.getMeridianIntegration("w-1");

    expect(result.ok).toBe(false);
  });
});
