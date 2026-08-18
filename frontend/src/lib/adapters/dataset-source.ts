import type { DatasetDetail, DatasetSummary } from "@/types/ui/commercial";
import type { PreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * The only data boundary the Dataset list/detail pages are allowed to
 * depend on -- mirrors ProjectSource's pattern. REQ-011/REQ-014
 * (docs/contracts/BACKEND_REQUESTS.md) specify the backend contract this
 * implements against; REQ-011's identity fields are real today, REQ-014's
 * lifecycle fields (source inventory, upload, evaluation history) don't
 * exist yet, so this fails loudly with a typed error (list/detail) or
 * returns honest nulls/empties (the lifecycle fields within detail) until
 * they do.
 */
export interface DatasetSource {
  listDatasets(workspaceId: string): Promise<PreM3ApiResult<DatasetSummary[]>>;
  getDataset(workspaceId: string, datasetId: string): Promise<PreM3ApiResult<DatasetDetail>>;
}
