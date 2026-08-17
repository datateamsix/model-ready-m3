import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockGetBillingSummary = vi.fn();
vi.mock("@/lib/adapters/api-billing-source", () => ({
  billingSource: { getBillingSummary: () => mockGetBillingSummary() },
}));

// The refresher's own polling behavior is covered by its dedicated test;
// this page test only needs to confirm it's mounted, not exercise it (it
// depends on next/navigation's App Router context, which isn't set up
// here).
vi.mock("@/components/prem3/checkout-success-refresher", () => ({
  CheckoutSuccessRefresher: () => null,
}));

import Page from "./page";

const PLAN_CATALOG_SUMMARY = {
  plan: "project",
  maxActiveProjects: 1,
  activeProjectCount: 0,
  renewsOrCancelsAtLabel: "Renews Sep 1",
  guidanceMessage: null,
  portalAvailable: true,
};

describe("/app/settings/billing", () => {
  it("renders an honest 'not connected yet' state when the backend billing endpoint is unconfigured (503)", async () => {
    mockGetBillingSummary.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });

    render(await Page());

    expect(screen.getByText("Billing isn't connected yet")).toBeInTheDocument();
  });

  it("renders a plain-language message for a known typed error code", async () => {
    mockGetBillingSummary.mockResolvedValue({
      ok: false,
      status: 502,
      error: { code: "PREM3_API_UNREACHABLE", message: "raw backend message", requestId: "r1" },
    });

    render(await Page());

    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't reach billing right now. Try again in a moment.");
  });

  it("falls back to the backend's own error message for an unknown error code -- never a fabricated one", async () => {
    mockGetBillingSummary.mockResolvedValue({
      ok: false,
      status: 500,
      error: { code: "SOME_NEW_BACKEND_ERROR", message: "exact backend wording", requestId: "r1" },
    });

    render(await Page());

    expect(screen.getByRole("alert")).toHaveTextContent("exact backend wording");
  });

  it("renders plan, usage, and renewal state from the real billing summary on success", async () => {
    mockGetBillingSummary.mockResolvedValue({ ok: true, data: PLAN_CATALOG_SUMMARY });

    render(await Page());

    expect(screen.getByText("0 of 1 active MMM Projects")).toBeInTheDocument();
    expect(screen.getByText("Renews Sep 1")).toBeInTheDocument();
  });

  it("shows server guidance copy when the backend provides it", async () => {
    mockGetBillingSummary.mockResolvedValue({
      ok: true,
      data: { ...PLAN_CATALOG_SUMMARY, guidanceMessage: "Your plan is past due." },
    });

    render(await Page());

    expect(screen.getByText("Your plan is past due.")).toBeInTheDocument();
  });
});
