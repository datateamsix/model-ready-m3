import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ScenarioCard } from "./scenario-card";
import type { ScenarioView } from "@/types/response";

const scenario: ScenarioView = {
  scenario_id: "s-1",
  title: "Add 8 weeks of additional history",
  assumption: "Assumes the additional weeks share the current schema and grain.",
  baseline_to_scenario: [{ dimension: "history", baseline: "131 weeks", scenario: "139 weeks" }],
  what_improves: "Parameter pressure on the media coefficients.",
  what_does_not_change: "Channel definitions and geo scope.",
  authority: "MMM_EVIDENCE_HEURISTIC",
  required_review: "Modeler review recommended before adoption.",
  read_only: true,
  production_data_changed: false,
};

describe("ScenarioCard", () => {
  it("marks a scenario as a read-only simulation and shows what it does and does not change", () => {
    render(<ScenarioCard scenario={scenario} />);
    expect(screen.getByText(scenario.title)).toBeInTheDocument();
    expect(screen.getByText(/read-only simulation/i)).toBeInTheDocument();
    expect(screen.getByText(scenario.what_improves)).toBeInTheDocument();
    expect(screen.getByText(scenario.what_does_not_change)).toBeInTheDocument();
  });
});
