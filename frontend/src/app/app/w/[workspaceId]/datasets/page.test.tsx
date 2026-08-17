import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockListDatasets = vi.fn();
vi.mock("@/lib/adapters/api-dataset-source", () => ({
  datasetSource: { listDatasets: (...args: unknown[]) => mockListDatasets(...args) },
}));

import Page from "./page";

function params(workspaceId: string) {
  return { params: Promise.resolve({ workspaceId }) };
}

describe("/app/w/[workspaceId]/datasets", () => {
  it("renders an honest 'not connected yet' state when REQ-011/014 are unconfigured (503)", async () => {
    mockListDatasets.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });

    render(await Page(params("w-1")));

    expect(screen.getByText("Datasets aren't connected yet")).toBeInTheDocument();
  });

  it("scopes the dataset list to the workspace from the route", async () => {
    mockListDatasets.mockResolvedValue({ ok: true, data: [] });

    render(await Page(params("w-42")));

    expect(mockListDatasets).toHaveBeenCalledWith("w-42");
  });

  it("renders real datasets with their KPI/grain and evaluation count, never a fabricated status", async () => {
    mockListDatasets.mockResolvedValue({
      ok: true,
      data: [
        {
          datasetId: "d-1",
          name: "Media spend export",
          kpiLabel: "Revenue",
          grainLabel: "Weekly",
          latestEvaluationStatus: null,
          latestEvaluatedAtLabel: null,
          evaluationCount: 3,
        },
      ],
    });

    render(await Page(params("w-1")));

    expect(screen.getByText("Media spend export")).toBeInTheDocument();
    expect(screen.getByText("3 evaluations")).toBeInTheDocument();
  });

  it("shows an honest empty state when the project genuinely has no datasets yet", async () => {
    mockListDatasets.mockResolvedValue({ ok: true, data: [] });

    render(await Page(params("w-1")));

    expect(screen.getByText("No Datasets yet")).toBeInTheDocument();
  });
});
