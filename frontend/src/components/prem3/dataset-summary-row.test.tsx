import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DatasetSummaryRow } from "./dataset-summary-row";
import type { DatasetSummary } from "@/types/ui/commercial";

const dataset: DatasetSummary = {
  datasetId: "ds-1",
  name: "National TV + Digital",
  kpiLabel: "Shopify orders",
  grainLabel: "Weekly x geo",
  latestEvaluationStatus: "READY",
  latestEvaluatedAtLabel: "Evaluated 3 hours ago",
  evaluationCount: 4,
};

describe("DatasetSummaryRow", () => {
  it("renders the dataset's name and real evaluation count, with no quota/cap language", () => {
    render(<DatasetSummaryRow dataset={dataset} workspaceId="ws-1" />);
    expect(screen.getByText("National TV + Digital")).toBeInTheDocument();
    expect(screen.getByText("4 evaluations")).toBeInTheDocument();
    expect(screen.queryByText(/of \d+ evaluations/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/remaining/i)).not.toBeInTheDocument();
  });

  it("links into the dataset detail route, not directly into a run", () => {
    render(<DatasetSummaryRow dataset={dataset} workspaceId="ws-1" />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/app/w/ws-1/datasets/ds-1");
  });
});
