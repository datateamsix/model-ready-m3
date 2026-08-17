import type { DatasetSource } from "./dataset-source";
import type { DatasetSummary } from "@/types/ui/commercial";
import { callPreM3Api, mapPreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * Mirrors prem3-api's DatasetResponse/DatasetListResponse
 * (contracts/openapi.yaml, frozen backend contract commit
 * `e045b4294e2bba36efa74b132e976e0959e2644b`). `dataset_id`/`workspace_id`/
 * `name`/`status`/`created_at`/`updated_at` only -- no KPI/grain/evaluation
 * fields exist on the backend yet (that's REQ-014, still NOT STARTED), so
 * the mapping below defaults those honestly rather than inventing them.
 */
interface DatasetResponse {
  dataset_id: string;
  workspace_id: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface DatasetListResponse {
  items: DatasetResponse[];
  next_cursor: string | null;
}

function toDatasetSummary(dataset: DatasetResponse): DatasetSummary {
  return {
    datasetId: dataset.dataset_id,
    name: dataset.name,
    kpiLabel: null,
    grainLabel: null,
    latestEvaluationStatus: null,
    latestEvaluatedAtLabel: null,
    evaluationCount: 0,
  };
}

/**
 * The real implementation of DatasetSource -- calls prem3-api's real
 * `/v1/workspaces/{workspace_id}/datasets` endpoint. Fails loudly with a
 * typed error (never a fabricated dataset list) until Clerk verification
 * lands (backend Mission 07).
 */
export class ApiDatasetSource implements DatasetSource {
  async listDatasets(workspaceId: string) {
    const result = await callPreM3Api<DatasetListResponse>(
      `v1/workspaces/${encodeURIComponent(workspaceId)}/datasets`,
    );
    return mapPreM3ApiResult(result, (data) => data.items.map(toDatasetSummary));
  }
}

export const datasetSource: DatasetSource = new ApiDatasetSource();
