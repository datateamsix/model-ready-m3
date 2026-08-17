import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { InsightCard } from "./insight-card";
import type { ResponseInsight } from "@/types/response";

const insight: ResponseInsight = {
  insight_id: "mel-not-proven",
  statement: "MEL promotion is not yet proven.",
  evidence_ids: ["lesson-count"],
  implication: "Automatic lesson promotion has not been demonstrated.",
  do_not_claim: "That PreM3 has already learned from production runs.",
  origin: "PREM3_INTERPRETATION",
};

describe("InsightCard", () => {
  it("renders the statement, implication, and an explicit do-not-claim guard", () => {
    render(<InsightCard insight={insight} />);
    expect(screen.getByText(insight.statement)).toBeInTheDocument();
    expect(screen.getByText(insight.implication)).toBeInTheDocument();
    expect(screen.getByText(/do not claim/i)).toBeInTheDocument();
    expect(screen.getByText(insight.do_not_claim as string)).toBeInTheDocument();
  });
});
