import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProjectAllowanceIndicator } from "./project-allowance-indicator";
import type { ProjectAllowanceSummary } from "@/types/ui/commercial";

describe("ProjectAllowanceIndicator", () => {
  it("renders the real used/max figures the entitlement projection gives it", () => {
    const allowance: ProjectAllowanceSummary = { activeProjectCount: 3, maxActiveProjects: 10 };
    render(<ProjectAllowanceIndicator allowance={allowance} />);
    expect(screen.getByText("3 of 10 active projects")).toBeInTheDocument();
  });

  it("does not compute or imply an upgrade decision when the allowance is exhausted", () => {
    const allowance: ProjectAllowanceSummary = { activeProjectCount: 1, maxActiveProjects: 1 };
    render(<ProjectAllowanceIndicator allowance={allowance} />);
    expect(screen.getByText("1 of 1 active projects")).toBeInTheDocument();
    expect(screen.queryByText(/upgrade/i)).not.toBeInTheDocument();
  });
});
