import type { DatasetSource } from "./dataset-source";
import type { DatasetSummary } from "@/types/ui/commercial";
import { callPreM3Api } from "@/lib/server/prem3-api-client";

/**
 * The real implementation of DatasetSource -- calls `prem3-api` through the
 * shared server-only client, against REQ-011/REQ-014
 * (docs/contracts/BACKEND_REQUESTS.md). Fails loudly with a typed error
 * (never a fabricated dataset list) until those endpoints exist.
 */
export class ApiDatasetSource implements DatasetSource {
  async listDatasets(workspaceId: string) {
    return callPreM3Api<DatasetSummary[]>(`v1/projects/${encodeURIComponent(workspaceId)}/datasets`);
  }
}

export const datasetSource: DatasetSource = new ApiDatasetSource();
