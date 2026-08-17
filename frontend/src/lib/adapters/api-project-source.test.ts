import { describe, expect, it, vi } from "vitest";

const mockCallPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/server/prem3-api-client")>(
    "@/lib/server/prem3-api-client",
  );
  return { ...actual, callPreM3Api: (...args: unknown[]) => mockCallPreM3Api(...args) };
});

import { ApiProjectSource } from "./api-project-source";

const WORKSPACE = {
  workspace_id: "w-1",
  name: "Q3 brand campaign",
  status: "ACTIVE",
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-02T00:00:00Z",
};

describe("ApiProjectSource", () => {
  it("lists workspaces from the real /v1/workspaces endpoint, mapped to ProjectSummary", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: { items: [WORKSPACE], next_cursor: null } });
    const source = new ApiProjectSource();

    const result = await source.listProjects();

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/workspaces");
    expect(result).toEqual({
      ok: true,
      data: [{ workspaceId: "w-1", name: "Q3 brand campaign", status: "ACTIVE", datasetCount: 0, latestActivityLabel: null }],
    });
  });

  it("creates a workspace with only the name -- no technical fields the backend doesn't accept", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: WORKSPACE });
    const source = new ApiProjectSource();

    const result = await source.createProject("Q3 brand campaign");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/workspaces", {
      method: "POST",
      body: JSON.stringify({ name: "Q3 brand campaign" }),
    });
    expect(result).toEqual({ ok: true, data: { workspaceId: "w-1" } });
  });

  it("reads a single workspace's detail by id from the real path", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: WORKSPACE });
    const source = new ApiProjectSource();

    const result = await source.getProject("w-1");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/workspaces/w-1");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.planningArtifactCount).toBeNull();
      expect(result.data.meridianIntegrationStatus).toBeNull();
    }
  });

  it("maps an ARCHIVED workspace status through, case-insensitively", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: { ...WORKSPACE, status: "archived" } });
    const source = new ApiProjectSource();

    const result = await source.getProject("w-1");

    expect(result.ok).toBe(true);
    if (result.ok) expect(result.data.status).toBe("ARCHIVED");
  });

  it("passes a typed error straight through without inventing a fallback project list", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 401,
      error: { code: "AUTH_PROVIDER_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiProjectSource();

    const result = await source.listProjects();

    expect(result.ok).toBe(false);
  });
});
