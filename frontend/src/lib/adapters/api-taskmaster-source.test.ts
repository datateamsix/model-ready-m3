import { describe, expect, it, vi } from "vitest";

const mockCallPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", () => ({
  callPreM3Api: (...args: unknown[]) => mockCallPreM3Api(...args),
}));

import { ApiTaskmasterSource } from "./api-taskmaster-source";

describe("ApiTaskmasterSource", () => {
  it("reads the Taskmaster read model scoped to the workspace, not a client-computed value", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: { workspaceId: "ws_1", stages: [] } });
    const source = new ApiTaskmasterSource();

    const result = await source.getTaskmaster("ws_1");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/projects/ws_1/taskmaster");
    expect(result.ok).toBe(true);
  });

  it("passes a typed error straight through without inventing a fallback read model", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiTaskmasterSource();

    const result = await source.getTaskmaster("ws_1");

    expect(result.ok).toBe(false);
  });
});
