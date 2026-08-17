import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BillingActions } from "./billing-actions";
import type { PlanCatalogEntry } from "@/types/ui/commercial";

const mockStartCheckout = vi.fn();
const mockOpenPortal = vi.fn();
vi.mock("@/app/app/settings/billing/actions", () => ({
  startCheckoutAction: (...args: unknown[]) => mockStartCheckout(...args),
  openBillingPortalAction: (...args: unknown[]) => mockOpenPortal(...args),
}));

const plans: PlanCatalogEntry[] = [
  {
    planId: "planner",
    displayName: "Planner",
    monthlyPriceDisplay: null,
    billingInterval: "monthly",
    maxActiveProjects: 0,
    ctaKind: "start_planner",
    ctaLabel: "Plan my MMM",
    stripeCheckoutAvailable: false,
    featureSummary: [],
  },
  {
    planId: "project",
    displayName: "Project",
    monthlyPriceDisplay: null,
    billingInterval: "monthly",
    maxActiveProjects: 1,
    ctaKind: "start_project",
    ctaLabel: "Start one project",
    stripeCheckoutAvailable: true,
    featureSummary: [],
  },
  {
    planId: "portfolio",
    displayName: "Portfolio",
    monthlyPriceDisplay: null,
    billingInterval: "monthly",
    maxActiveProjects: 10,
    ctaKind: "start_project",
    ctaLabel: "Choose Portfolio",
    stripeCheckoutAvailable: true,
    featureSummary: [],
  },
  {
    planId: "enterprise",
    displayName: "Enterprise",
    monthlyPriceDisplay: null,
    billingInterval: "monthly",
    maxActiveProjects: 50,
    ctaKind: "contact_sales",
    ctaLabel: "Contact sales",
    stripeCheckoutAvailable: false,
    featureSummary: [],
  },
];

describe("BillingActions", () => {
  it("offers checkout only for plans that support it and aren't the current plan", () => {
    render(<BillingActions plans={plans} currentPlan="project" portalAvailable={true} />);

    expect(screen.getByRole("button", { name: "Choose Portfolio" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start one project" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Plan my MMM" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Contact sales" })).not.toBeInTheDocument();
  });

  it("shows Manage billing only when the backend says a portal session is available", () => {
    const { rerender } = render(<BillingActions plans={plans} currentPlan="project" portalAvailable={true} />);
    expect(screen.getByRole("button", { name: "Manage billing" })).toBeInTheDocument();

    rerender(<BillingActions plans={plans} currentPlan="project" portalAvailable={false} />);
    expect(screen.queryByRole("button", { name: "Manage billing" })).not.toBeInTheDocument();
    expect(screen.getByText(/isn't available yet/i)).toBeInTheDocument();
  });

  it("carries the target plan's stable plan_id via a hidden field, not a client-owned Stripe Price ID", () => {
    render(<BillingActions plans={plans} currentPlan="project" portalAvailable={true} />);

    const hiddenInput = document.querySelector('input[name="planId"]') as HTMLInputElement;
    expect(hiddenInput.value).toBe("portfolio");
  });

  it("renders a server-returned error message instead of silently failing", async () => {
    mockStartCheckout.mockResolvedValue({
      errorCode: "PREM3_API_NOT_CONFIGURED",
      errorMessage: "Billing isn't connected yet.",
    });
    const user = userEvent.setup();
    render(<BillingActions plans={plans} currentPlan="project" portalAvailable={true} />);

    await user.click(screen.getByRole("button", { name: "Choose Portfolio" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Billing isn't connected yet.");
  });
});
