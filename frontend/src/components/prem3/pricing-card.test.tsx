import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PricingCard } from "./pricing-card";
import type { PlanCatalogEntry } from "@/types/ui/commercial";

const projectPlan: PlanCatalogEntry = {
  planId: "project",
  displayName: "Project",
  monthlyPriceDisplay: null,
  billingInterval: "monthly",
  maxActiveProjects: 1,
  ctaKind: "start_project",
  ctaLabel: "Start one project",
  stripeCheckoutAvailable: false,
  featureSummary: ["Unlimited re-evaluations"],
};

describe("PricingCard", () => {
  it("renders the plan's real 1-project figure unmistakably, not a vague description", () => {
    render(<PricingCard plan={projectPlan} />);
    expect(screen.getByText("1 active MMM Project")).toBeInTheDocument();
  });

  it("renders an honest placeholder, never an invented dollar amount, when price isn't configured yet", () => {
    render(<PricingCard plan={projectPlan} />);
    expect(screen.queryByText(/\$\d/)).not.toBeInTheDocument();
    expect(screen.getByText(/pricing/i)).toBeInTheDocument();
  });

  it("renders the plan's own real CTA label and routes it into the real funnel, not a fabricated checkout", () => {
    render(<PricingCard plan={projectPlan} />);
    expect(screen.getByRole("link", { name: "Start one project" })).toHaveAttribute("href", "/start");
  });
});
