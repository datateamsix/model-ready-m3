import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockGetTaskmaster = vi.fn();
vi.mock("@/lib/adapters/api-taskmaster-source", () => ({
  taskmasterSource: { getTaskmaster: (...args: unknown[]) => mockGetTaskmaster(...args) },
}));

import Page from "./page";

function renderPage(workspaceId = "ws_1") {
  return Page({ params: Promise.resolve({ workspaceId }) });
}

const GATE_EVIDENCE = {
  gate_status: "READY",
  bigquery_verified: true,
  content_fingerprint_matched: true,
  official_meridian_eda_complete: true,
  official_error_count: 0,
  handoff_persisted: true,
  review_recommended: false,
  evidence_ids: [],
};

function stageFixture(overrides: Record<string, unknown> = {}) {
  return {
    stageId: "map",
    label: "Map",
    status: "COMPLETE",
    objective: "Map every source column to the Meridian input schema.",
    known: [],
    missing: [],
    owner: "PREM3",
    requiresApproval: false,
    currentTask: null,
    detail: null,
    ...overrides,
  };
}

describe("/app/w/[workspaceId]/taskmaster", () => {
  it("renders an honest 'not connected yet' state when the backend Taskmaster endpoint is unconfigured (503)", async () => {
    mockGetTaskmaster.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });

    render(await renderPage());

    expect(screen.getByText("Taskmaster isn't connected yet")).toBeInTheDocument();
    expect(mockGetTaskmaster).toHaveBeenCalledWith("ws_1");
  });

  it("falls back to the backend's own error message for an unknown error code -- never a fabricated one", async () => {
    mockGetTaskmaster.mockResolvedValue({
      ok: false,
      status: 500,
      error: { code: "SOME_NEW_BACKEND_ERROR", message: "exact backend wording", requestId: "r1" },
    });

    render(await renderPage());

    expect(screen.getByRole("alert")).toHaveTextContent("exact backend wording");
  });

  it("renders the stage rail and the current stage's detail straight from the read model", async () => {
    mockGetTaskmaster.mockResolvedValue({
      ok: true,
      data: {
        workspaceId: "ws_1",
        datasetId: null,
        runId: null,
        currentStageId: "mend",
        stages: [
          stageFixture({ stageId: "map", label: "Map", status: "COMPLETE" }),
          stageFixture({ stageId: "mend", label: "Mend", status: "USER_ACTION_REQUIRED", objective: "Fix the schema mismatch." }),
        ],
        modelReady: null,
      },
    });

    render(await renderPage());

    expect(screen.getByTestId("taskmaster-stage-map")).toBeInTheDocument();
    expect(screen.getByTestId("taskmaster-stage-mend")).toHaveAttribute("data-current", "true");
    expect(screen.getByText("Fix the schema mismatch.")).toBeInTheDocument();
  });

  it("shows an honest empty state when the backend returns zero stages, rather than a fabricated ledger", async () => {
    mockGetTaskmaster.mockResolvedValue({
      ok: true,
      data: { workspaceId: "ws_1", datasetId: null, runId: null, currentStageId: null, stages: [], modelReady: null },
    });

    render(await renderPage());

    expect(screen.getByText("No Taskmaster stages yet")).toBeInTheDocument();
  });

  it("renders ModelReadyCard only when the backend's gate evidence is present -- never inferred from stage completion", async () => {
    mockGetTaskmaster.mockResolvedValue({
      ok: true,
      data: {
        workspaceId: "ws_1",
        datasetId: null,
        runId: null,
        currentStageId: "map",
        stages: [stageFixture()],
        modelReady: { title: "Model Ready", summary: "Verified model-ready package.", status: "READY", gate: GATE_EVIDENCE },
      },
    });

    render(await renderPage());

    expect(screen.getByText("Model Ready")).toBeInTheDocument();
    expect(screen.getByText("Verified model-ready package.")).toBeInTheDocument();
  });

  it("never renders ModelReadyCard when the backend has not supplied gate evidence", async () => {
    mockGetTaskmaster.mockResolvedValue({
      ok: true,
      data: {
        workspaceId: "ws_1",
        datasetId: null,
        runId: null,
        currentStageId: "map",
        stages: [stageFixture()],
        modelReady: null,
      },
    });

    render(await renderPage());

    expect(screen.queryByTestId("gate-bigquery_verified")).not.toBeInTheDocument();
  });
});
