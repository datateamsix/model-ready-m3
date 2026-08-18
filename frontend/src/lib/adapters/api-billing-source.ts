import type { BillingSource } from "./billing-source";
import type { BillingSummary, CheckoutSessionResult, PlanId, PortalSessionResult } from "@/types/ui/commercial";
import { callPreM3Api, mapPreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * Mirrors prem3-api's real contract, confirmed against contracts/
 * openapi.yaml at backend Mission 08 commit `d9461a7` (docs/contracts/
 * BACKEND_REQUESTS.md's REQ-013 entry -- read that first, it's already
 * fact-checked). `GET /v1/me` returns a nested MeResponse, not this
 * frontend's flat BillingSummary -- `renewsOrCancelsAtLabel` and
 * `guidanceMessage` have no contract field yet (defaulted to null, never
 * fabricated). There is no `portalAvailable`-equivalent field on the real
 * `MePlan`/`MeOrganization` schemas -- Portal must always be offered as the
 * billing recovery path (see billing-actions.tsx), never gated on a
 * fabricated flag here.
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

/** `return_path` must be a relative path -- the backend builds the full
 * redirect from it (REQ-013). Both Checkout and Portal return here so a
 * user always lands back on billing settings regardless of which flow they
 * took. */
const BILLING_RETURN_PATH = "/app/settings/billing";

function toBillingSummary(me: MeResponse): BillingSummary {
  return {
    plan: me.plan.plan_id as PlanId,
    planStatus: me.plan.status,
    maxActiveProjects: me.project_capacity.max_active_projects,
    activeProjectCount: me.project_capacity.active_projects,
    renewsOrCancelsAtLabel: null,
    guidanceMessage: null,
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
      headers: { "Idempotency-Key": globalThis.crypto.randomUUID() },
      body: JSON.stringify({ plan_id: planId, return_path: BILLING_RETURN_PATH }),
    });
    return mapPreM3ApiResult<BillingSessionResponse, CheckoutSessionResult>(result, (session) => ({
      redirectUrl: session.url,
    }));
  }

  async createPortalSession() {
    const result = await callPreM3Api<BillingSessionResponse>("v1/billing/portal-session", {
      method: "POST",
      body: JSON.stringify({ return_path: BILLING_RETURN_PATH }),
    });
    return mapPreM3ApiResult<BillingSessionResponse, PortalSessionResult>(result, (session) => ({
      redirectUrl: session.url,
    }));
  }
}

export const billingSource: BillingSource = new ApiBillingSource();
