import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockGetProject = vi.fn();
vi.mock("@/lib/adapters/api-project-source", () => ({
  projectSource: { getProject: (...args: unknown[]) => mockGetProject(...args) },
}));

import Page from "./page";

function params(workspaceId: string) {
  return { params: Promise.resolve({ workspaceId }) };
}

describe("/app/w/[workspaceId]", () => {
  it("renders an honest 'not connected yet' state when REQ-016 is unconfigured (503)", async () => {
    mockGetProject.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });

    render(await Page(params("w-1")));

    expect(screen.getByText("MMM Project isn't connected yet")).toBeInTheDocument();
  });

  it("passes the workspaceId from the route straight through to the data source", async () => {
    mockGetProject.mockResolvedValue({
      ok: true,
      data: {
        workspaceId: "w-42",
        name: "Q3 brand campaign",
        status: "ACTIVE",
        datasetCount: 3,
        planningArtifactCount: null,
        latestEvaluationState: null,
        meridianIntegrationStatus: null,
      },
    });

    render(await Page(params("w-42")));

    expect(mockGetProject).toHaveBeenCalledWith("w-42");
    expect(screen.getByText("Q3 brand campaign")).toBeInTheDocument();
  });

  it("shows 'not yet available' rather than a fabricated status for fields the backend doesn't return yet", async () => {
    mockGetProject.mockResolvedValue({
      ok: true,
      data: {
        workspaceId: "w-1",
        name: "Q3 brand campaign",
        status: "ACTIVE",
        datasetCount: 0,
        planningArtifactCount: null,
        latestEvaluationState: null,
        meridianIntegrationStatus: null,
      },
    });

    render(await Page(params("w-1")));

    expect(screen.getAllByText("Not yet available").length).toBeGreaterThan(0);
  });

  it("links each section to the real route for that MMM Project", async () => {
    mockGetProject.mockResolvedValue({
      ok: true,
      data: {
        workspaceId: "w-1",
        name: "Q3",
        status: "ACTIVE",
        datasetCount: 0,
        planningArtifactCount: null,
        latestEvaluationState: null,
        meridianIntegrationStatus: null,
      },
    });

    render(await Page(params("w-1")));

    expect(screen.getByRole("link", { name: /Datasets/ })).toHaveAttribute("href", "/app/w/w-1/datasets");
    expect(screen.getByRole("link", { name: /Planning/ })).toHaveAttribute("href", "/app/w/w-1/plans");
    expect(screen.getByRole("link", { name: /Taskmaster/ })).toHaveAttribute("href", "/app/w/w-1/taskmaster");
    expect(screen.getByRole("link", { name: /Meridian Integration/ })).toHaveAttribute(
      "href",
      "/app/w/w-1/meridian",
    );
  });
});
