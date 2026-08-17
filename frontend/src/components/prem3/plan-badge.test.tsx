import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PlanBadge } from "./plan-badge";
import type { PlanSummary } from "@/types/ui/commercial";

const plan: PlanSummary = { planId: "portfolio", displayName: "Portfolio", maxActiveProjects: 10 };

describe("PlanBadge", () => {
  it("renders the plan's own display name verbatim, not a re-derived label", () => {
    render(<PlanBadge plan={plan} />);
    expect(screen.getByText("Portfolio")).toBeInTheDocument();
  });
});
