import type { AcquisitionPlanDetail } from "@/types/ui/commercial";
import type { PreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * The only data boundary the acquisition plan detail page is allowed to
 * depend on. REQ-010 (docs/contracts/BACKEND_REQUESTS.md) specifies the
 * backend contract this implements against; it's still NOT STARTED (same
 * backend surface as M2-10's planning intake, also out of scope this
 * session), so this fails loudly with a typed error until it exists.
 */
export interface PlanSource {
  getPlan(workspaceId: string, planningRunId: string): Promise<PreM3ApiResult<AcquisitionPlanDetail>>;
}
