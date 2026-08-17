import type { DatasetSummary } from "@/types/ui/commercial";
import type { PreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * The only data boundary the Dataset list is allowed to depend on --
 * mirrors ProjectSource's pattern. REQ-011/REQ-014
 * (docs/contracts/BACKEND_REQUESTS.md) specify the backend contract this
 * implements against; neither exists yet, so this fails loudly with a
 * typed error until they do.
 */
export interface DatasetSource {
  listDatasets(workspaceId: string): Promise<PreM3ApiResult<DatasetSummary[]>>;
}
