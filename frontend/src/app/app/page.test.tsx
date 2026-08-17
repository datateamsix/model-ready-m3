import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockGetBillingSummary = vi.fn();
vi.mock("@/lib/adapters/api-billing-source", () => ({
  billingSource: { getBillingSummary: () => mockGetBillingSummary() },
}));

const mockListProjects = vi.fn();
vi.mock("@/lib/adapters/api-project-source", () => ({
  projectSource: { listProjects: () => mockListProjects() },
}));

vi.mock("@/components/prem3/create-project-form", () => ({
  CreateProjectForm: () => null,
}));

import Page from "./page";

const BASE_SUMMARY = {
  plan: "project",
  maxActiveProjects: 1,
  activeProjectCount: 0,
  renewsOrCancelsAtLabel: null,
  guidanceMessage: null,
  portalAvailable: true,
};

describe("/app dashboard", () => {
  it("renders an honest 'not connected yet' state when identity/entitlement is unconfigured (503)", async () => {
    mockGetBillingSummary.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });

    render(await Page());

    expect(screen.getByText("Dashboard isn't connected yet")).toBeInTheDocument();
  });

  it("shows plan and active-project usage as real figures, not invented ones", async () => {
    mockGetBillingSummary.mockResolvedValue({ ok: true, data: { ...BASE_SUMMARY, activeProjectCount: 0 } });
    mockListProjects.mockResolvedValue({ ok: true, data: [] });

    render(await Page());

    expect(screen.getByText("0 of 1 active MMM Projects")).toBeInTheDocument();
  });

  it("shows an upgrade CTA when at the plan's project limit", async () => {
    mockGetBillingSummary.mockResolvedValue({ ok: true, data: { ...BASE_SUMMARY, activeProjectCount: 1 } });
    mockListProjects.mockResolvedValue({ ok: true, data: [] });

    render(await Page());

    expect(screen.getByRole("link", { name: "Upgrade" })).toHaveAttribute("href", "/pricing");
  });

  it("shows a 'choose a plan' CTA for a plan with no project slots", async () => {
    mockGetBillingSummary.mockResolvedValue({
      ok: true,
      data: { ...BASE_SUMMARY, plan: "planner", maxActiveProjects: 0, activeProjectCount: 0 },
    });
    mockListProjects.mockResolvedValue({ ok: true, data: [] });

    render(await Page());

    expect(screen.getByRole("link", { name: "Choose a plan" })).toHaveAttribute("href", "/pricing");
  });

  it("renders an honest gap state for the project list until REQ-016 exists, without blocking the rest of the page", async () => {
    mockGetBillingSummary.mockResolvedValue({ ok: true, data: BASE_SUMMARY });
    mockListProjects.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });

    render(await Page());

    expect(screen.getByText("Project list isn't connected yet")).toBeInTheDocument();
    expect(screen.getByText("0 of 1 active MMM Projects")).toBeInTheDocument();
  });

  it("renders real projects from the backend when they exist", async () => {
    mockGetBillingSummary.mockResolvedValue({ ok: true, data: BASE_SUMMARY });
    mockListProjects.mockResolvedValue({
      ok: true,
      data: [{ workspaceId: "w-1", name: "Q3 brand campaign", status: "ACTIVE", datasetCount: 2, latestActivityLabel: "Updated 2 days ago" }],
    });

    render(await Page());

    expect(screen.getByText("Q3 brand campaign")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Q3 brand campaign/ })).toHaveAttribute("href", "/app/w/w-1");
  });

  it("always links to the fixture-backed pipeline demo, clearly labeled as not the user's data", async () => {
    mockGetBillingSummary.mockResolvedValue({ ok: true, data: BASE_SUMMARY });
    mockListProjects.mockResolvedValue({ ok: true, data: [] });

    render(await Page());

    expect(screen.getByText(/not your data/i)).toBeInTheDocument();
  });
});
