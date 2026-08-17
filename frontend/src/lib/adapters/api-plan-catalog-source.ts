import type { PlanCatalogSource } from "./plan-catalog-source";
import type { PlanCatalogEntry, PlanCtaKind, PlanId } from "@/types/ui/commercial";
import { callPublicPreM3Api, mapPreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * Mirrors prem3-api's real PlanCatalogEntry/PlanCatalogResponse
 * (contracts/openapi.yaml, frozen backend contract commit
 * `e045b4294e2bba36efa74b132e976e0959e2644b`). `GET /v1/catalog/plans` is
 * genuinely public (no `HTTPBearer` security requirement) -- uses
 * callPublicPreM3Api, never callPreM3Api, so this works signed-out.
 */
interface ApiPlanCatalogEntry {
  plan_id: string;
  display_name: string;
  description: string;
  max_active_projects: number;
  feature_summary: string[];
  billing_interval: string;
  checkout_eligible: boolean;
  unlimited_reevaluations: boolean;
  amount: number | null;
  currency: string | null;
  display_price: string | null;
}

interface PlanCatalogResponse {
  plans: ApiPlanCatalogEntry[];
}

function toCtaKind(planId: string, checkoutEligible: boolean): PlanCtaKind {
  if (planId === "planner") return "start_planner";
  if (!checkoutEligible) return "contact_sales";
  return "start_project";
}

function toPlanCatalogEntry(entry: ApiPlanCatalogEntry): PlanCatalogEntry {
  return {
    planId: entry.plan_id as PlanId,
    displayName: entry.display_name,
    monthlyPriceDisplay: entry.display_price,
    billingInterval: "monthly",
    maxActiveProjects: entry.max_active_projects,
    ctaKind: toCtaKind(entry.plan_id, entry.checkout_eligible),
    ctaLabel: entry.plan_id === "planner" ? "Plan my MMM" : entry.checkout_eligible ? "Choose plan" : "Contact sales",
    stripeCheckoutAvailable: entry.checkout_eligible,
    featureSummary: entry.feature_summary,
  };
}

/**
 * The real implementation of PlanCatalogSource -- calls prem3-api's real
 * public `/v1/catalog/plans`. Not wired into `/pricing` yet: no
 * `PREM3_API_BASE_URL` is configured anywhere tonight, so swapping this in
 * now would replace the working fixture-backed pricing page with a "not
 * connected yet" empty state -- strictly worse for the hackathon demo than
 * the honest, complete fixture page that exists today. Ready to flip
 * (`planCatalogSource` swaps to `new ApiPlanCatalogSource()` in
 * fixture-plan-catalog-source.ts's place) the moment a real backend URL
 * exists -- that's the whole point of the PlanCatalogSource abstraction.
 */
export class ApiPlanCatalogSource implements PlanCatalogSource {
  async listPlans() {
    const result = await callPublicPreM3Api<PlanCatalogResponse>("v1/catalog/plans");
    const mapped = mapPreM3ApiResult(result, (data) => data.plans.map(toPlanCatalogEntry));
    if (!mapped.ok) {
      // PlanCatalogSource's interface (M2-05, pre-dates any real backend)
      // has no error channel -- `Promise<PlanCatalogEntry[]>`, not a
      // PreM3ApiResult. Silently returning [] would misrepresent "couldn't
      // reach the catalog" as "no plans exist," which is exactly the kind
      // of fabrication this codebase's documented-gap discipline forbids.
      // Throwing surfaces the real failure to whatever page/error-boundary
      // calls this; the interface itself should move to a Result type
      // before this adapter is actually wired into a live page.
      throw new Error(`Plan catalog unavailable: ${mapped.error.code} (${mapped.error.message})`);
    }
    return mapped.data;
  }
}

export const apiPlanCatalogSource: PlanCatalogSource = new ApiPlanCatalogSource();
