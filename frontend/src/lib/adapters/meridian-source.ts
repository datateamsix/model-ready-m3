import type { MeridianIntegrationSummary } from "@/types/ui/commercial";
import type { PreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * The only data boundary the Meridian Integration surface is allowed to
 * depend on. REQ-017 (docs/contracts/BACKEND_REQUESTS.md) specifies the
 * backend contract this implements against; it's a newly filed gap (no
 * request covered this surface before M2-14), so this fails loudly with a
 * typed error until it exists.
 */
export interface MeridianSource {
  getMeridianIntegration(workspaceId: string): Promise<PreM3ApiResult<MeridianIntegrationSummary>>;
}
