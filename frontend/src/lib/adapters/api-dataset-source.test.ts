import { describe, expect, it, vi } from "vitest";

const mockCallPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", () => ({
  callPreM3Api: (...args: unknown[]) => mockCallPreM3Api(...args),
}));

import { ApiDatasetSource } from "./api-dataset-source";

describe("ApiDatasetSource", () => {
  it("lists datasets scoped to the given MMM Project", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: [] });
    const source = new ApiDatasetSource();

    await source.listDatasets("w-1");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/projects/w-1/datasets");
  });

  it("passes a typed error straight through without inventing a fallback dataset list", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiDatasetSource();

    const result = await source.listDatasets("w-1");

    expect(result.ok).toBe(false);
  });
});
