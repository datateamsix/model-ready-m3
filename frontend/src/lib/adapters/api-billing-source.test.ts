import { describe, expect, it, vi } from "vitest";

const mockCallPreM3Api = vi.fn();
vi.mock("@/lib/server/prem3-api-client", () => ({
  callPreM3Api: (...args: unknown[]) => mockCallPreM3Api(...args),
}));

import { ApiBillingSource } from "./api-billing-source";

describe("ApiBillingSource", () => {
  it("reads the billing summary from /v1/me, not a client-computed value", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: { plan: "project" } });
    const source = new ApiBillingSource();

    const result = await source.getBillingSummary();

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/me");
    expect(result).toEqual({ ok: true, data: { plan: "project" } });
  });

  it("creates a checkout session keyed by the stable plan_id, never a client-owned Stripe Price ID", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: { redirectUrl: "https://checkout.stripe.com/x" } });
    const source = new ApiBillingSource();

    const result = await source.createCheckoutSession("portfolio");

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_id: "portfolio" }),
    });
    expect(result).toEqual({ ok: true, data: { redirectUrl: "https://checkout.stripe.com/x" } });
  });

  it("creates a portal session with no client-supplied body", async () => {
    mockCallPreM3Api.mockResolvedValue({ ok: true, data: { redirectUrl: "https://billing.stripe.com/p" } });
    const source = new ApiBillingSource();

    const result = await source.createPortalSession();

    expect(mockCallPreM3Api).toHaveBeenCalledWith("v1/billing/portal", { method: "POST" });
    expect(result).toEqual({ ok: true, data: { redirectUrl: "https://billing.stripe.com/p" } });
  });

  it("passes a typed error straight through without inventing a fallback summary", async () => {
    mockCallPreM3Api.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });
    const source = new ApiBillingSource();

    const result = await source.getBillingSummary();

    expect(result.ok).toBe(false);
  });
});
