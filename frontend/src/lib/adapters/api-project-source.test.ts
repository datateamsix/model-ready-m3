import { describe, expect, it, vi } from "vitest";

const mockCallPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", () => ({
  callPreM3Api: (...args: unknown[]) => mockCallPreM3Api(...args),
}));

import { ApiProjectSource } from "./api-project-source";

describe("ApiProjectSource", () => {
  it("lists projects from v1/projects", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: [] });
    const source = new ApiProjectSource();

    const result = await source.listProjects();

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/projects");
    expect(result).toEqual({ ok: true, data: [] });
  });

  it("creates a project with only the name -- no client-supplied technical fields", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: { workspaceId: "w-1" } });
    const source = new ApiProjectSource();

    const result = await source.createProject("Q3 brand campaign");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/projects", {
      method: "POST",
      body: JSON.stringify({ name: "Q3 brand campaign" }),
    });
    expect(result).toEqual({ ok: true, data: { workspaceId: "w-1" } });
  });

  it("reads a single project's detail by workspace id", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: { workspaceId: "w-1", name: "Q3" } });
    const source = new ApiProjectSource();

    await source.getProject("w-1");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/projects/w-1");
  });

  it("passes a typed error straight through without inventing a fallback project list", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiProjectSource();

    const result = await source.listProjects();

    expect(result.ok).toBe(false);
  });
});
