import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ModelReadyCard } from "./model-ready-card";
import type { ModelReadyGateEvidence } from "@/types/response";

const passingGate: ModelReadyGateEvidence = {
  gate_status: "MODEL_READY",
  bigquery_verified: true,
  content_fingerprint_matched: true,
  official_meridian_eda_complete: true,
  official_error_count: 0,
  handoff_persisted: true,
  review_recommended: false,
  evidence_ids: [],
};

describe("ModelReadyCard", () => {
  it("renders every gate field's real value, including the ERROR count", () => {
    render(
      <ModelReadyCard
        title="MODEL_READY"
        summary="The pre-modeling contract has been verified."
        status="READY"
        gate={passingGate}
      />,
    );
    expect(screen.getByText("BigQuery model artifact")).toBeInTheDocument();
    expect(screen.getByText("Official ERROR count: 0")).toBeInTheDocument();
  });

  it("renders a failed gate field as not-passed rather than glossing over it", () => {
    const notReadyGate: ModelReadyGateEvidence = { ...passingGate, bigquery_verified: false };
    render(
      <ModelReadyCard title="Not ready" summary="BigQuery publish parity has not passed." status="BLOCKED" gate={notReadyGate} />,
    );
    const row = screen.getByTestId("gate-bigquery_verified");
    expect(row).toHaveAttribute("data-passed", "false");
  });

  it("surfaces review_recommended as a visible note when true, without changing the status it was given", () => {
    const reviewGate: ModelReadyGateEvidence = { ...passingGate, review_recommended: true };
    render(
      <ModelReadyCard title="MODEL_READY" summary="s" status="REVIEW_RECOMMENDED" gate={reviewGate} />,
    );
    // "Review recommended" also appears in the StatusHeader's status badge
    // for this status, so this asserts the explanatory note specifically.
    expect(
      screen.getByText(/review recommended — official meridian/i),
    ).toBeInTheDocument();
  });
});
