import { describe, expect, it, vi } from "vitest";

const mockCallPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/server/prem3-api-client")>(
    "@/lib/server/prem3-api-client",
  );
  return { ...actual, callPreM3Api: (...args: unknown[]) => mockCallPreM3Api(...args) };
});

import { ApiBillingSource } from "./api-billing-source";

const ME_RESPONSE = {
  user: { user_id: "u-1" },
  organization: { tenant_id: "t-1", display_name: "Acme" },
  plan: { plan_id: "project", status: "active", feature_summary: [] },
  project_capacity: { active_projects: 1, max_active_projects: 1, remaining_projects: 0 },
};

describe("ApiBillingSource", () => {
  it("reads the billing summary from the real nested /v1/me shape, not a client-computed value", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: ME_RESPONSE });
    const source = new ApiBillingSource();

    const result = await source.getBillingSummary();

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/me");
    expect(result).toEqual({
      ok: true,
      data: {
        plan: "project",
        maxActiveProjects: 1,
        activeProjectCount: 1,
        renewsOrCancelsAtLabel: null,
        guidanceMessage: null,
        portalAvailable: false,
      },
    });
  });

  it("creates a checkout session against the real checkout-session path, keyed by the stable plan_id", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: { url: "https://checkout.stripe.com/x", expires_at: null } });
    const source = new ApiBillingSource();

    const result = await source.createCheckoutSession("portfolio");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/billing/checkout-session", {
      method: "POST",
      body: JSON.stringify({ plan_id: "portfolio" }),
    });
    expect(result).toEqual({ ok: true, data: { redirectUrl: "https://checkout.stripe.com/x" } });
  });

  it("creates a portal session against the real portal-session path with no client-supplied customer ID", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: { url: "https://billing.stripe.com/p", expires_at: null } });
    const source = new ApiBillingSource();

    const result = await source.createPortalSession();

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/billing/portal-session", {
      method: "POST",
      body: JSON.stringify({}),
    });
    expect(result).toEqual({ ok: true, data: { redirectUrl: "https://billing.stripe.com/p" } });
  });

  it("passes a typed error straight through without inventing a fallback summary", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 401,
      error: { code: "AUTH_PROVIDER_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiBillingSource();

    const result = await source.getBillingSummary();

    expect(result.ok).toBe(false);
  });
});
