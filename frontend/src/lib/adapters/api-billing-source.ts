import type { BillingSource } from "./billing-source";
import type { BillingSummary, CheckoutSessionResult, PlanId, PortalSessionResult } from "@/types/ui/commercial";
import { callPreM3Api, mapPreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * Mirrors prem3-api's real contract (contracts/openapi.yaml, frozen
 * backend contract commit `e045b4294e2bba36efa74b132e976e0959e2644b`).
 * `GET /v1/me` returns a nested MeResponse, not this frontend's flat
 * BillingSummary -- `renewsOrCancelsAtLabel` and `guidanceMessage` have no
 * contract field yet (defaulted to null, never fabricated).
 * `portalAvailable` has no contract field either; defaulting to false
 * (safe/honest -- "unknown whether there's a Stripe customer to manage")
 * rather than inferring it from plan_id, which would be a guess dressed up
 * as data.
 */
interface MeResponse {
  user: { user_id: string };
  organization: { tenant_id: string; display_name: string };
  plan: { plan_id: string; status: string; feature_summary: string[] };
  project_capacity: { active_projects: number; max_active_projects: number; remaining_projects: number };
}

interface BillingSessionResponse {
  url: string;
  expires_at: string | null;
}

function toBillingSummary(me: MeResponse): BillingSummary {
  return {
    plan: me.plan.plan_id as PlanId,
    maxActiveProjects: me.project_capacity.max_active_projects,
    activeProjectCount: me.project_capacity.active_projects,
    renewsOrCancelsAtLabel: null,
    guidanceMessage: null,
    portalAvailable: false,
  };
}

/**
 * The real implementation of BillingSource -- calls prem3-api's real
 * `/v1/me` and `/v1/billing/*-session` endpoints. Fails loudly with a
 * typed error (never a fabricated summary or a client-simulated
 * subscription) until Clerk verification (Mission 07) and Stripe
 * configuration land.
 */
export class ApiBillingSource implements BillingSource {
  async getBillingSummary() {
    const result = await callPreM3Api<MeResponse>("v1/me");
    return mapPreM3ApiResult(result, toBillingSummary);
  }

  async createCheckoutSession(planId: PlanId) {
    const result = await callPreM3Api<BillingSessionResponse>("v1/billing/checkout-session", {
      method: "POST",
      body: JSON.stringify({ plan_id: planId }),
    });
    return mapPreM3ApiResult<BillingSessionResponse, CheckoutSessionResult>(result, (session) => ({
      redirectUrl: session.url,
    }));
  }

  async createPortalSession() {
    const result = await callPreM3Api<BillingSessionResponse>("v1/billing/portal-session", {
      method: "POST",
      body: JSON.stringify({}),
    });
    return mapPreM3ApiResult<BillingSessionResponse, PortalSessionResult>(result, (session) => ({
      redirectUrl: session.url,
    }));
  }
}

export const billingSource: BillingSource = new ApiBillingSource();
