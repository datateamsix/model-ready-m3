import { describe, expect, it, vi } from "vitest";

const mockCallPublicPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/server/prem3-api-client")>(
    "@/lib/server/prem3-api-client",
  );
  return { ...actual, callPublicPreM3Api: (...args: unknown[]) => mockCallPublicPreM3Api(...args) };
});

import { ApiPlanCatalogSource } from "./api-plan-catalog-source";

const PROJECT_ENTRY = {
  plan_id: "project",
  display_name: "Project",
  description: "One active MMM Project.",
  max_active_projects: 1,
  feature_summary: ["Unlimited re-evaluations"],
  billing_interval: "monthly",
  checkout_eligible: true,
  unlimited_reevaluations: true,
  amount: null,
  currency: null,
  display_price: null,
};

describe("ApiPlanCatalogSource", () => {
  it("calls the real public catalog endpoint without authentication", async () => {
    mockCallPublicPreM3Api.mockResolvedValue({ ok: true, data: { plans: [] } });
    const source = new ApiPlanCatalogSource();

    await source.listPlans();

    expect(mockCallPublicPreM3Api).toHaveBeenCalledWith("v1/catalog/plans");
  });

  it("maps a checkout-eligible plan to a stable stripeCheckoutAvailable flag and CTA", async () => {
    mockCallPublicPreM3Api.mockResolvedValue({ ok: true, data: { plans: [PROJECT_ENTRY] } });
    const source = new ApiPlanCatalogSource();

    const plans = await source.listPlans();

    expect(plans[0]).toMatchObject({ planId: "project", stripeCheckoutAvailable: true, ctaKind: "start_project" });
  });

  it("maps a null display_price honestly, never inventing a dollar amount", async () => {
    mockCallPublicPreM3Api.mockResolvedValue({ ok: true, data: { plans: [PROJECT_ENTRY] } });
    const source = new ApiPlanCatalogSource();

    const plans = await source.listPlans();

    expect(plans[0].monthlyPriceDisplay).toBeNull();
  });

  it("throws rather than silently returning an empty list when the catalog is unreachable", async () => {
    mockCallPublicPreM3Api.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiPlanCatalogSource();

    await expect(source.listPlans()).rejects.toThrow("PREM3_API_NOT_CONFIGURED");
  });
});
