import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RunTimeline } from "./run-timeline";

describe("RunTimeline", () => {
  it("renders every golden-path stage with its human label", () => {
    render(<RunTimeline currentStage="VALIDATING" failed={false} />);
    expect(screen.getByText("Map")).toBeInTheDocument();
    expect(screen.getByText("Validate")).toBeInTheDocument();
    expect(screen.getByText("Explore")).toBeInTheDocument();
    expect(screen.getByText("Model ready")).toBeInTheDocument();
  });

  it("marks the current stage distinctly from completed and not-started stages", () => {
    render(<RunTimeline currentStage="VALIDATING" failed={false} />);
    expect(screen.getByTestId("stage-VALIDATING")).toHaveAttribute("data-status", "ACTIVE");
    expect(screen.getByTestId("stage-MAPPING")).toHaveAttribute("data-status", "COMPLETE");
    expect(screen.getByTestId("stage-PUBLISHING")).toHaveAttribute("data-status", "NOT_STARTED");
  });

  it("marks the current stage FAILED when the run failed, without implying later stages ran", () => {
    render(<RunTimeline currentStage="REMEDIATING" failed />);
    expect(screen.getByTestId("stage-REMEDIATING")).toHaveAttribute("data-status", "FAILED");
    expect(screen.getByTestId("stage-VALIDATING")).toHaveAttribute("data-status", "NOT_STARTED");
  });

  it("keeps prior golden-path progress visible while a run is off-path waiting for approval", () => {
    // WAITING_FOR_APPROVAL is a real RunStage (app/core/state.py) that sits
    // off RUN_STAGE_ORDER's golden path -- it has no dot of its own here,
    // but the golden-path stages around it must still render honestly
    // rather than every dot collapsing to NOT_STARTED.
    render(<RunTimeline currentStage="WAITING_FOR_APPROVAL" failed={false} />);
    expect(screen.getByTestId("stage-ASSESSING")).toHaveAttribute("data-status", "COMPLETE");
    expect(screen.getByTestId("stage-REMEDIATING")).toHaveAttribute("data-status", "NOT_STARTED");
    expect(screen.getByTestId("stage-VALIDATING")).toHaveAttribute("data-status", "NOT_STARTED");
  });
});
