import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TaskmasterCurrentStage } from "./taskmaster-current-stage";
import { datasetAAssessmentResponse } from "@/lib/fixtures/responses";
import type { TaskmasterStage } from "@/types/ui/taskmaster";

function stage(overrides: Partial<TaskmasterStage>): TaskmasterStage {
  return {
    stageId: "mend",
    label: "Mend",
    status: "USER_ACTION_REQUIRED",
    objective: "Repair the schema mismatch before proceeding.",
    known: [],
    missing: [],
    owner: "PREM3",
    requiresApproval: false,
    currentTask: null,
    detail: null,
    ...overrides,
  };
}

describe("TaskmasterCurrentStage", () => {
  it("renders the stage's objective, status, and owner straight from backend data", () => {
    render(<TaskmasterCurrentStage stage={stage({ owner: "ANALYST" })} />);

    expect(screen.getByText("Mend")).toBeInTheDocument();
    expect(screen.getByText("Repair the schema mismatch before proceeding.")).toBeInTheDocument();
    expect(screen.getByText("User action required")).toBeInTheDocument();
    expect(screen.getByText("Analyst")).toBeInTheDocument();
  });

  it("labels a PreM3 owner as autonomous, distinct from a human owner", () => {
    render(<TaskmasterCurrentStage stage={stage({ owner: "PREM3" })} />);

    expect(screen.getByText("PreM3 (autonomous)")).toBeInTheDocument();
  });

  it("shows the current task only when the backend provides one", () => {
    const { rerender } = render(<TaskmasterCurrentStage stage={stage({ currentTask: null })} />);
    expect(screen.queryByText(/current task/i)).not.toBeInTheDocument();

    rerender(<TaskmasterCurrentStage stage={stage({ currentTask: "Confirm the channel mapping" })} />);
    expect(screen.getByText(/current task: confirm the channel mapping/i)).toBeInTheDocument();
  });

  it("shows an Approval required tag only when the backend requires it", () => {
    render(<TaskmasterCurrentStage stage={stage({ requiresApproval: true })} />);
    expect(screen.getByText("Approval required")).toBeInTheDocument();
  });

  it("renders known and missing exactly as given, without inferring readiness", () => {
    render(
      <TaskmasterCurrentStage
        stage={stage({ known: ["Channel taxonomy"], missing: ["Promo calendar"] })}
      />,
    );

    expect(screen.getByText("Known")).toBeInTheDocument();
    expect(screen.getByText("Channel taxonomy")).toBeInTheDocument();
    expect(screen.getByText("Missing")).toBeInTheDocument();
    expect(screen.getByText("Promo calendar")).toBeInTheDocument();
  });

  it("reuses ResponsePanel and ProofDrawer when the backend supplies a full stage detail", () => {
    render(<TaskmasterCurrentStage stage={stage({ detail: datasetAAssessmentResponse })} />);

    expect(screen.getByText(datasetAAssessmentResponse.title)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /view proof/i })).toBeInTheDocument();
  });

  it("never renders a response panel or proof drawer when detail is null", () => {
    render(<TaskmasterCurrentStage stage={stage({ detail: null })} />);

    expect(screen.queryByRole("button", { name: /view proof/i })).not.toBeInTheDocument();
  });
});
