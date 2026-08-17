import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TaskmasterStageRail } from "./taskmaster-stage-rail";
import type { TaskmasterStage } from "@/types/ui/taskmaster";

function stage(overrides: Partial<TaskmasterStage>): TaskmasterStage {
  return {
    stageId: "map",
    label: "Map",
    status: "PENDING",
    objective: "",
    known: [],
    missing: [],
    owner: "PREM3",
    requiresApproval: false,
    currentTask: null,
    detail: null,
    ...overrides,
  };
}

describe("TaskmasterStageRail", () => {
  it("renders each stage's backend-supplied status via StatusBadge, never a computed one", () => {
    const stages = [
      stage({ stageId: "map", label: "Map", status: "COMPLETE" }),
      stage({ stageId: "mend", label: "Mend", status: "USER_ACTION_REQUIRED" }),
    ];

    render(<TaskmasterStageRail stages={stages} currentStageId={null} />);

    expect(screen.getByText("Map")).toBeInTheDocument();
    expect(screen.getByText("Complete")).toBeInTheDocument();
    expect(screen.getByText("Mend")).toBeInTheDocument();
    expect(screen.getByText("User action required")).toBeInTheDocument();
  });

  it("marks only the stage matching currentStageId as current, without altering any status", () => {
    const stages = [
      stage({ stageId: "map", status: "COMPLETE" }),
      stage({ stageId: "mend", status: "PENDING" }),
    ];

    render(<TaskmasterStageRail stages={stages} currentStageId="mend" />);

    expect(screen.getByTestId("taskmaster-stage-map")).toHaveAttribute("data-current", "false");
    expect(screen.getByTestId("taskmaster-stage-mend")).toHaveAttribute("data-current", "true");
    // Still shows Pending, not flipped to an "active" status just for being current.
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("shows an Approval required tag only when the backend sets requiresApproval", () => {
    const stages = [
      stage({ stageId: "map", requiresApproval: false }),
      stage({ stageId: "mend", requiresApproval: true }),
    ];

    render(<TaskmasterStageRail stages={stages} currentStageId={null} />);

    expect(screen.getAllByText("Approval required")).toHaveLength(1);
  });
});
