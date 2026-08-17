import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EvaluationHistoryRow } from "./evaluation-history-row";
import type { EvaluationHistoryEntry } from "@/types/ui/commercial";

const evaluation: EvaluationHistoryEntry = {
  runId: "run-42",
  status: "READY",
  evaluatedAtLabel: "Aug 17, 2026",
};

describe("EvaluationHistoryRow", () => {
  it("renders the evaluation's real status and timestamp label, distinct from a dataset row", () => {
    render(<EvaluationHistoryRow evaluation={evaluation} workspaceId="ws-1" datasetId="ds-1" />);
    expect(screen.getByText("Aug 17, 2026")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("links into the specific run under the dataset, not the dataset itself", () => {
    render(<EvaluationHistoryRow evaluation={evaluation} workspaceId="ws-1" datasetId="ds-1" />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/app/w/ws-1/datasets/ds-1/runs/run-42");
  });
});
