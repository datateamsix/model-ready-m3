import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { FindingCard } from "./finding-card";
import type { ResponseFinding } from "@/types/response";

const baseFinding: ResponseFinding = {
  finding_id: "f-1",
  title: "Duplicate Google Ads row",
  observed_fact: "One exact duplicate campaign row was found on 2025-03-12 for TX.",
  evidence: [],
  interpretation: "This inflates spend for that geo/week unless removed.",
  why_it_matters: "Duplicate rows distort weekly spend totals fed into Meridian.",
  knowledge_class: "PREM3_DETERMINISTIC_DIAGNOSTIC",
  decision_class: "AUTO_SAFE",
  knowledge_authority_label: "PreM3 deterministic diagnostic",
  decision_authority_label: "Auto-safe remediation",
  disposition: "PASS",
  origin: "RUN_EVIDENCE",
  affected_entities: [],
  source_refs: [],
  related_action_ids: [],
  technical_proof_refs: [],
  official_severity: null,
  official_finding_text: null,
  prem3_interpretation: null,
};

describe("FindingCard", () => {
  it("renders the observed fact and interpretation as separately labeled blocks", () => {
    render(<FindingCard finding={baseFinding} />);
    const observedLabel = screen.getByText(/^observed$/i);
    const interpretationLabel = screen.getByText(/^interpretation$/i);
    expect(observedLabel).toBeInTheDocument();
    expect(interpretationLabel).toBeInTheDocument();
    expect(observedLabel.closest("section")).not.toBe(interpretationLabel.closest("section"));
    expect(screen.getByText(baseFinding.observed_fact)).toBeInTheDocument();
    expect(screen.getByText(baseFinding.interpretation as string)).toBeInTheDocument();
  });

  it("does not render an interpretation block when interpretation is null", () => {
    render(<FindingCard finding={{ ...baseFinding, interpretation: null }} />);
    expect(screen.queryByText(/^interpretation$/i)).not.toBeInTheDocument();
    expect(screen.getByText(/^observed$/i)).toBeInTheDocument();
  });
});
