import type { PlanCatalogEntry } from "@/types/ui/commercial";

/**
 * UI_DEMO_FIXTURE
 *
 * REQ-012 (docs/contracts/BACKEND_REQUESTS.md) -- the public Plan Catalog
 * backend endpoint -- doesn't exist yet, so /pricing renders from this
 * fixture via FixturePlanCatalogSource. monthlyPriceDisplay is null for
 * every plan: the commercial model spec is explicit that dollar amounts
 * are never invented in the frontend, so "not yet configured" is rendered
 * honestly rather than a plausible-looking placeholder price. Feature
 * summaries are drawn directly from the Mission 2 prompt pack's own M2-05
 * plan definitions -- nothing here invents SSO, SLAs, procurement, or any
 * other enterprise-only capability the pack explicitly warns against
 * fabricating.
 */
export const planCatalogFixture: PlanCatalogEntry[] = [
  {
    planId: "planner",
    displayName: "Planner",
    monthlyPriceDisplay: null,
    billingInterval: "monthly",
    maxActiveProjects: 0,
    ctaKind: "start_planner",
    ctaLabel: "Plan my MMM",
    stripeCheckoutAvailable: false,
    featureSummary: ["Public PreM3 Planner", "No paid MMM Project slot", "No dataset processing"],
  },
  {
    planId: "project",
    displayName: "Project",
    monthlyPriceDisplay: null,
    billingInterval: "monthly",
    maxActiveProjects: 1,
    ctaKind: "start_project",
    ctaLabel: "Start one project",
    stripeCheckoutAvailable: false,
    featureSummary: [
      "Multiple related datasets inside the project",
      "Unlimited re-evaluations",
      "Mapping and readiness assessment",
      "Safe remediation",
      "Official Meridian EDA",
      "Model-ready validation",
      "BigQuery publish and verification",
      "Meridian Integration",
    ],
  },
  {
    planId: "portfolio",
    displayName: "Portfolio",
    monthlyPriceDisplay: null,
    billingInterval: "monthly",
    maxActiveProjects: 10,
    ctaKind: "start_project",
    ctaLabel: "Choose Portfolio",
    stripeCheckoutAvailable: false,
    featureSummary: ["Everything in Project", "Built for agencies and multi-brand teams"],
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
    featureSummary: ["Everything in Portfolio"],
  },
];
