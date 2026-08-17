import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockAuth = vi.fn();
vi.mock("@clerk/nextjs/server", () => ({
  auth: () => mockAuth(),
}));

const mockGetBillingSummary = vi.fn();
vi.mock("@/lib/adapters/api-billing-source", () => ({
  billingSource: { getBillingSummary: () => mockGetBillingSummary() },
}));

const mockListProjects = vi.fn();
vi.mock("@/lib/adapters/api-projects-source", () => ({
  projectsSource: { listProjects: () => mockListProjects(), createProject: vi.fn() },
}));

// CreateProjectForm is a client component with its own dedicated tests;
// this page test only needs to confirm it's mounted with the right stage.
vi.mock("@/components/prem3/create-project-form", () => ({
  CreateProjectForm: ({ stage, label }: { stage: string; label: string }) => (
    <div data-testid={`create-project-form-${stage}`}>{label}</div>
  ),
}));

import Page from "./page";

function pageWithSearchParams(stage?: string) {
  return Page({ searchParams: Promise.resolve(stage ? { stage } : {}) });
}

const SIGNED_OUT = { userId: null };
const SIGNED_IN = { userId: "user_123" };

const NOT_CONFIGURED_ERROR = {
  ok: false as const,
  status: 503,
  error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
};

describe("/start", () => {
  afterEach(() => {
    mockAuth.mockReset();
    mockGetBillingSummary.mockReset();
    mockListProjects.mockReset();
  });

  it("always renders all three equal-weight cards with the pack's exact card copy", async () => {
    mockAuth.mockResolvedValue(SIGNED_OUT);

    render(await pageWithSearchParams());

    expect(screen.getByRole("heading", { name: "Planning" })).toBeInTheDocument();
    expect(screen.getByText("I have not collected the data yet.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Getting organized" })).toBeInTheDocument();
    expect(screen.getByText("I have some data, but not a complete plan or dataset.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ready to assess" })).toBeInTheDocument();
    expect(screen.getByText("My data is assembled.")).toBeInTheDocument();
  });

  it("routes the Planning card straight to /planner without any auth or backend call", async () => {
    mockAuth.mockResolvedValue(SIGNED_OUT);

    render(await pageWithSearchParams());

    expect(screen.getByRole("link", { name: /start planning/i })).toHaveAttribute("href", "/planner");
    expect(mockGetBillingSummary).not.toHaveBeenCalled();
    expect(mockListProjects).not.toHaveBeenCalled();
  });

  it("never calls the billing/projects adapters at all when signed out", async () => {
    mockAuth.mockResolvedValue(SIGNED_OUT);

    render(await pageWithSearchParams());

    expect(mockGetBillingSummary).not.toHaveBeenCalled();
    expect(mockListProjects).not.toHaveBeenCalled();
  });

  it("signed out: getting-organized and ready-to-assess link to sign-up preserving the stage as a redirect target", async () => {
    mockAuth.mockResolvedValue(SIGNED_OUT);

    render(await pageWithSearchParams());

    const signUpLinks = screen.getAllByRole("link", { name: /sign up to continue/i });
    expect(signUpLinks).toHaveLength(2);
    expect(signUpLinks[0]).toHaveAttribute(
      "href",
      "/sign-up?redirect_url=%2Fstart%3Fstage%3Dgetting-organized",
    );
    expect(signUpLinks[1]).toHaveAttribute(
      "href",
      "/sign-up?redirect_url=%2Fstart%3Fstage%3Dready-to-assess",
    );
  });

  it("signed in but backend not configured (today's real state): shows an honest blocked message, not a fabricated project list", async () => {
    mockAuth.mockResolvedValue(SIGNED_IN);
    mockGetBillingSummary.mockResolvedValue(NOT_CONFIGURED_ERROR);
    mockListProjects.mockResolvedValue(NOT_CONFIGURED_ERROR);

    render(await pageWithSearchParams());

    expect(screen.getAllByText(/REQ-003, REQ-011/)).toHaveLength(2);
    expect(screen.queryByTestId("create-project-form-getting-organized")).not.toBeInTheDocument();
    expect(screen.queryByTestId("create-project-form-ready-to-assess")).not.toBeInTheDocument();
  });

  it("signed in, free plan with no active-project slot and no existing projects: routes to pricing instead of a fabricated project", async () => {
    mockAuth.mockResolvedValue(SIGNED_IN);
    mockGetBillingSummary.mockResolvedValue({
      ok: true,
      data: { plan: "planner", maxActiveProjects: 0, activeProjectCount: 0, renewsOrCancelsAtLabel: null, guidanceMessage: null, portalAvailable: false },
    });
    mockListProjects.mockResolvedValue({ ok: true, data: [] });

    render(await pageWithSearchParams());

    const pricingLinks = screen.getAllByRole("link", { name: /choose a plan/i });
    expect(pricingLinks).toHaveLength(2);
    for (const link of pricingLinks) {
      expect(link).toHaveAttribute("href", "/pricing");
    }
  });

  it("signed in, paid plan with an available slot and no existing projects: offers project creation, no auto-created project", async () => {
    mockAuth.mockResolvedValue(SIGNED_IN);
    mockGetBillingSummary.mockResolvedValue({
      ok: true,
      data: { plan: "project", maxActiveProjects: 1, activeProjectCount: 0, renewsOrCancelsAtLabel: null, guidanceMessage: null, portalAvailable: true },
    });
    mockListProjects.mockResolvedValue({ ok: true, data: [] });

    render(await pageWithSearchParams());

    expect(screen.getByTestId("create-project-form-getting-organized")).toBeInTheDocument();
    expect(screen.getByTestId("create-project-form-ready-to-assess")).toBeInTheDocument();
    // Rendering the page must never itself create a project.
    expect(mockListProjects).toHaveBeenCalledTimes(1);
  });

  it("signed in with existing projects: offers Continue links into the right next route per card", async () => {
    mockAuth.mockResolvedValue(SIGNED_IN);
    mockGetBillingSummary.mockResolvedValue({
      ok: true,
      data: { plan: "portfolio", maxActiveProjects: 10, activeProjectCount: 1, renewsOrCancelsAtLabel: null, guidanceMessage: null, portalAvailable: true },
    });
    mockListProjects.mockResolvedValue({
      ok: true,
      data: [{ workspaceId: "ws_1", name: "Acme MMM", status: "ACTIVE", datasetCount: 2, latestActivityLabel: "Updated 2 days ago" }],
    });

    render(await pageWithSearchParams());

    const continueLinks = screen.getAllByRole("link", { name: /acme mmm/i });
    expect(continueLinks).toHaveLength(2);
    expect(continueLinks[0]).toHaveAttribute("href", "/app/w/ws_1/plans");
    expect(continueLinks[1]).toHaveAttribute("href", "/app/w/ws_1/datasets");
  });

  it("signed in, at the plan's project limit but with existing projects: still offers Continue, but not project creation", async () => {
    mockAuth.mockResolvedValue(SIGNED_IN);
    mockGetBillingSummary.mockResolvedValue({
      ok: true,
      data: { plan: "project", maxActiveProjects: 1, activeProjectCount: 1, renewsOrCancelsAtLabel: null, guidanceMessage: null, portalAvailable: true },
    });
    mockListProjects.mockResolvedValue({
      ok: true,
      data: [{ workspaceId: "ws_1", name: "Acme MMM", status: "ACTIVE", datasetCount: 2, latestActivityLabel: null }],
    });

    render(await pageWithSearchParams());

    expect(screen.getAllByRole("link", { name: /acme mmm/i })).toHaveLength(2);
    expect(screen.queryByTestId("create-project-form-getting-organized")).not.toBeInTheDocument();
    expect(screen.getAllByText(/at your plan's project limit/i)).toHaveLength(2);
  });

  it("highlights the card matching the ?stage= query param without auto-creating anything", async () => {
    mockAuth.mockResolvedValue(SIGNED_OUT);

    render(await pageWithSearchParams("getting-organized"));

    expect(mockListProjects).not.toHaveBeenCalled();
    const gettingOrganizedHeading = screen.getByRole("heading", { name: "Getting organized" });
    const card = gettingOrganizedHeading.closest("div.rounded-lg");
    expect(card?.className).toMatch(/ring-2/);
  });
});
