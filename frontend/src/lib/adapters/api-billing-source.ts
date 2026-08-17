import type { BillingSource } from "./billing-source";
import type { BillingSummary, CheckoutSessionResult, PlanId, PortalSessionResult } from "@/types/ui/commercial";
import { callPreM3Api } from "@/lib/server/prem3-api-client";

/**
 * The real implementation of BillingSource -- calls `prem3-api` through the
 * shared server-only client. Every method fails loudly with a typed error
 * (never a fabricated summary or a client-simulated subscription) until
 * REQ-003 (`/v1/me`) and REQ-013 (billing endpoints) exist; see
 * prem3-api-client.ts's documented-gap discipline.
 */
export class ApiBillingSource implements BillingSource {
  async getBillingSummary() {
    return callPreM3Api<BillingSummary>("v1/me");
  }

  async createCheckoutSession(planId: PlanId) {
    return callPreM3Api<CheckoutSessionResult>("v1/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_id: planId }),
    });
  }

  async createPortalSession() {
    return callPreM3Api<PortalSessionResult>("v1/billing/portal", { method: "POST" });
  }
}

export const billingSource: BillingSource = new ApiBillingSource();
