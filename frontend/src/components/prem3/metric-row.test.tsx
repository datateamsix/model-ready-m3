import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricRow } from "./metric-row";
import type { ResponseMetric } from "@/types/response";

const metrics: ResponseMetric[] = [
  { metric_id: "official-errors", label: "Official ERROR count", value: 0, evidence_id: "gate-errors", unit: null },
  { metric_id: "promoted-lessons", label: "Promoted experiential lessons", value: 0, evidence_id: "lesson-count", unit: null },
];

describe("MetricRow", () => {
  it("renders every metric's label and value, including a real zero value", () => {
    render(<MetricRow metrics={metrics} />);
    expect(screen.getByText("Official ERROR count")).toBeInTheDocument();
    expect(screen.getAllByText("0")).toHaveLength(2);
  });

  it("renders nothing when there are no metrics", () => {
    const { container } = render(<MetricRow metrics={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
