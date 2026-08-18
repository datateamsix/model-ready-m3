import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockGetDataset = vi.fn();
vi.mock("@/lib/adapters/api-dataset-source", () => ({
  datasetSource: { getDataset: (...args: unknown[]) => mockGetDataset(...args) },
}));

import Page from "./page";

function params(workspaceId: string, datasetId: string) {
  return { params: Promise.resolve({ workspaceId, datasetId }) };
}

const REAL_DATASET = {
  datasetId: "d-1",
  workspaceId: "w-1",
  name: "Media spend export",
  status: "ACTIVE",
  createdAtLabel: "Aug 1, 2026",
  updatedAtLabel: "Aug 2, 2026",
  sourceCount: null,
  uploadState: null,
  latestEvaluationStatus: null,
  latestEvaluatedAtLabel: null,
  evaluationHistory: [],
  artifactCount: null,
};

describe("/app/w/[workspaceId]/datasets/[datasetId]", () => {
  it("renders an honest 'not connected yet' state when REQ-011 is unconfigured (503)", async () => {
    mockGetDataset.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });

    render(await Page(params("w-1", "d-1")));

    expect(screen.getByText("This dataset isn't connected yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Back to datasets/ })).toHaveAttribute(
      "href",
      "/app/w/w-1/datasets",
    );
  });

  it("scopes the lookup to both the workspace and dataset from the route", async () => {
    mockGetDataset.mockResolvedValue({ ok: true, data: REAL_DATASET });

    render(await Page(params("w-42", "d-9")));

    expect(mockGetDataset).toHaveBeenCalledWith("w-42", "d-9");
  });

  it("renders real dataset identity, never a fabricated status", async () => {
    mockGetDataset.mockResolvedValue({ ok: true, data: REAL_DATASET });

    render(await Page(params("w-1", "d-1")));

    expect(screen.getByRole("heading", { name: "Media spend export" })).toBeInTheDocument();
    expect(screen.getByText(/Created Aug 1, 2026/)).toBeInTheDocument();
  });

  it("shows honest 'not yet available' notes for every REQ-014 lifecycle section, never invented data", async () => {
    mockGetDataset.mockResolvedValue({ ok: true, data: REAL_DATASET });

    render(await Page(params("w-1", "d-1")));

    expect(screen.getByText(/prem3-api doesn't return source inventory yet/)).toBeInTheDocument();
    expect(screen.getByText(/never a client-held credential/)).toBeInTheDocument();
    expect(screen.getByText("No evaluations yet")).toBeInTheDocument();
    expect(screen.getByText(/prem3-api doesn't return artifacts yet/)).toBeInTheDocument();
  });

  it("disables 'Run another evaluation' rather than offering a fake run", async () => {
    mockGetDataset.mockResolvedValue({ ok: true, data: REAL_DATASET });

    render(await Page(params("w-1", "d-1")));

    expect(screen.getByRole("button", { name: "Run another evaluation" })).toBeDisabled();
  });

  it("renders real evaluation history rows when the backend supplies them, still no run-quota UI", async () => {
    mockGetDataset.mockResolvedValue({
      ok: true,
      data: {
        ...REAL_DATASET,
        evaluationHistory: [{ runId: "r-1", status: "READY", evaluatedAtLabel: "Aug 3, 2026" }],
      },
    });

    render(await Page(params("w-1", "d-1")));

    expect(screen.getByText("Aug 3, 2026")).toBeInTheDocument();
    expect(screen.queryByText(/of \d+ evaluations/)).not.toBeInTheDocument();
  });
});
