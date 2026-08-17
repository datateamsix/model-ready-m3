import { describe, expect, it, vi } from "vitest";

const mockCallPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", () => ({
  callPreM3Api: (...args: unknown[]) => mockCallPreM3Api(...args),
}));

import { ApiProjectsSource } from "./api-projects-source";

describe("ApiProjectsSource", () => {
  it("lists projects from /v1/projects, not a client-computed value", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: [] });
    const source = new ApiProjectsSource();

    const result = await source.listProjects();

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/projects");
    expect(result).toEqual({ ok: true, data: [] });
  });

  it("creates a project with only the name in the request body", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: true,
      data: { workspaceId: "ws_1", name: "Acme MMM", status: "ACTIVE", datasetCount: 0, latestActivityLabel: null },
    });
    const source = new ApiProjectsSource();

    const result = await source.createProject("Acme MMM");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/projects", {
      method: "POST",
      body: JSON.stringify({ name: "Acme MMM" }),
    });
    expect(result.ok).toBe(true);
  });

  it("passes a typed error straight through without inventing a fallback project list", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiProjectsSource();

    const result = await source.listProjects();

    expect(result.ok).toBe(false);
  });
});
