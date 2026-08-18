import { describe, expect, it, vi } from "vitest";

const mockCallPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/server/prem3-api-client")>(
    "@/lib/server/prem3-api-client",
  );
  return { ...actual, callPreM3Api: (...args: unknown[]) => mockCallPreM3Api(...args) };
});

import { ApiDatasetSource } from "./api-dataset-source";

describe("ApiDatasetSource", () => {
  it("lists datasets from the real /v1/workspaces/{id}/datasets endpoint, mapped to DatasetSummary", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: true,
      data: {
        items: [
          {
            dataset_id: "d-1",
            workspace_id: "w-1",
            name: "Media spend export",
            status: "ACTIVE",
            created_at: "2026-08-01T00:00:00Z",
            updated_at: "2026-08-02T00:00:00Z",
          },
        ],
        next_cursor: null,
      },
    });
    const source = new ApiDatasetSource();

    const result = await source.listDatasets("w-1");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/workspaces/w-1/datasets");
    expect(result).toEqual({
      ok: true,
      data: [
        {
          datasetId: "d-1",
          name: "Media spend export",
          kpiLabel: null,
          grainLabel: null,
          latestEvaluationStatus: null,
          latestEvaluatedAtLabel: null,
          evaluationCount: 0,
        },
      ],
    });
  });

  it("passes a typed error straight through without inventing a fallback dataset list", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 401,
      error: { code: "AUTH_PROVIDER_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiDatasetSource();

    const result = await source.listDatasets("w-1");

    expect(result.ok).toBe(false);
  });
});

describe("ApiDatasetSource.getDataset", () => {
  it("fetches a single Dataset from the real /v1/workspaces/{id}/datasets/{id} endpoint", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: true,
      data: {
        dataset_id: "d-1",
        workspace_id: "w-1",
        name: "Media spend export",
        status: "ACTIVE",
        created_at: "2026-08-01T00:00:00Z",
        updated_at: "2026-08-02T00:00:00Z",
      },
    });
    const source = new ApiDatasetSource();

    const result = await source.getDataset("w-1", "d-1");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/workspaces/w-1/datasets/d-1");
    expect(result).toEqual({
      ok: true,
      data: {
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
      },
    });
  });

  it("passes a typed error straight through without inventing a fallback dataset", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 404,
      error: { code: "RESOURCE_NOT_FOUND", message: "not found", requestId: "r1" },
    });
    const source = new ApiDatasetSource();

    const result = await source.getDataset("w-1", "missing");

    expect(result.ok).toBe(false);
  });
});
