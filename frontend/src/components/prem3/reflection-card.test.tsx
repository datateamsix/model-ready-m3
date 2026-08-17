import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReflectionCard } from "./reflection-card";
import type { ExperienceReflection } from "@/types/mel";

// The plan's literal buildReflection() omitted episode_fingerprint,
// domain_view_fingerprint_used, content_fingerprint, and reflection_role --
// all required fields added to ExperienceReflection during Task 7's
// field-for-field verification against app/mel/models.py. Filled in here
// with the same UI_DEMO_FIXTURE-style illustrative placeholders used in
// lib/fixtures/experience.ts (Task 11).
function buildReflection(overrides: Partial<ExperienceReflection> = {}): ExperienceReflection {
  return {
    reflection_id: "r-1",
    episode_id: "e-1",
    run_id: "run-1",
    episode_fingerprint: "UI_DEMO_FIXTURE-episode-fingerprint",
    domain_view_version_used: "1.0.0",
    domain_view_fingerprint_used: "UI_DEMO_FIXTURE-domain-view-fingerprint",
    created_at: "2026-08-16T09:14:00Z",
    known_at_decision_time: [],
    observed: [
      { item_id: "i-1", surface: "OBSERVED", statement: "5 issues detected.", origin: "RUN_EVIDENCE", evidence_refs: [] },
    ],
    determined: [],
    believed: [],
    allowed: [],
    unknown: [],
    expected: [],
    actual_outcome: [],
    confirmed: [],
    missed: [],
    incomplete: [],
    human_added: [],
    meridian_added: [],
    effective_actions: [],
    ineffective_or_unnecessary_actions: [],
    surprises: [],
    possible_improvements: [],
    generalization_risk: "LOW",
    reflection_summary: "Reached MODEL_READY as expected.",
    content_fingerprint: "UI_DEMO_FIXTURE-reflection-fingerprint",
    operational_authority: false,
    reflection_role: "TRAINING",
    ...overrides,
  };
}

describe("ReflectionCard", () => {
  it("always visibly states that reflection has no operational authority", () => {
    render(<ReflectionCard reflection={buildReflection()} />);
    expect(screen.getByText(/no operational authority/i)).toBeInTheDocument();
  });

  it("renders non-empty reflection surfaces and their statements", () => {
    render(<ReflectionCard reflection={buildReflection()} />);
    expect(screen.getByText("5 issues detected.")).toBeInTheDocument();
  });

  it("omits empty reflection surfaces rather than rendering empty sections", () => {
    render(<ReflectionCard reflection={buildReflection()} />);
    expect(screen.queryByText(/^believed$/i)).not.toBeInTheDocument();
  });
});
