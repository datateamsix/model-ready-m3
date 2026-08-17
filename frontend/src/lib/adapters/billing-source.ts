import type { BillingSummary, CheckoutSessionResult, PlanId, PortalSessionResult } from "@/types/ui/commercial";
import type { PreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * The only data boundary the billing settings page and its Server Actions
 * are allowed to depend on -- mirrors PlanCatalogSource's pattern
 * (src/lib/adapters/plan-catalog-source.ts). Every method returns
 * prem3-api-client.ts's typed Result rather than throwing, so callers
 * render a real error state instead of an unhandled exception.
 */
export interface BillingSource {
  getBillingSummary(): Promise<PreM3ApiResult<BillingSummary>>;
  createCheckoutSession(planId: PlanId): Promise<PreM3ApiResult<CheckoutSessionResult>>;
  createPortalSession(): Promise<PreM3ApiResult<PortalSessionResult>>;
}
