import { describe, expect, it } from "vitest";
import { generatePlannerResult } from "./decision-engine";
import { EMPTY_PLANNER_INTAKE, type PlannerIntake } from "./types";
import { PLANNING_GUIDANCE_DISCLAIMER } from "./manifest";

const FIXED_NOW = new Date("2026-08-17T12:00:00.000Z");

function intake(overrides: Partial<PlannerIntake>): PlannerIntake {
  return { ...EMPTY_PLANNER_INTAKE, ...overrides };
}

describe("generatePlannerResult", () => {
  it("is deterministic -- the same intake always produces the same result", () => {
    const input = intake({ channelCategoryIds: ["paid_search"], historyLengthMonths: 12 });

    const first = generatePlannerResult(input, FIXED_NOW);
    const second = generatePlannerResult(input, FIXED_NOW);

    expect(first).toEqual(second);
  });

  it("always carries the planning-guidance disclaimer, never a readiness certification", () => {
    const result = generatePlannerResult(intake({}), FIXED_NOW);
    expect(result.disclaimer).toBe(PLANNING_GUIDANCE_DISCLAIMER);
  });

  it("maps selected channel categories to real registry providers, not fabricated ones", () => {
    const result = generatePlannerResult(intake({ channelCategoryIds: ["paid_search"] }), FIXED_NOW);

    expect(result.dataAcquisitionMap).toHaveLength(1);
    expect(result.dataAcquisitionMap[0].channelLabel).toBe("Paid Search");
    const providerIds = result.dataAcquisitionMap[0].likelyProviders.map((p) => p.providerId);
    expect(providerIds).toContain("google_ads");
  });

  it("narrows to the specific platforms the user picked when they picked any", () => {
    const result = generatePlannerResult(
      intake({ channelCategoryIds: ["paid_search"], providerIds: ["microsoft_ads"] }),
      FIXED_NOW,
    );

    const providerIds = result.dataAcquisitionMap[0].likelyProviders.map((p) => p.providerId);
    expect(providerIds).toEqual(["microsoft_ads"]);
  });

  it("flags under-6-months history as a known gap", () => {
    const result = generatePlannerResult(intake({ historyLengthMonths: 3 }), FIXED_NOW);
    expect(result.knownGaps.some((gap) => gap.includes("6 months"))).toBe(true);
  });

  it("does not flag history as a gap once 6+ months are provided", () => {
    const result = generatePlannerResult(intake({ historyLengthMonths: 12 }), FIXED_NOW);
    expect(result.knownGaps.some((gap) => gap.includes("6 months"))).toBe(false);
  });

  it("flags having no outcome data source at all as a known gap", () => {
    const result = generatePlannerResult(
      intake({ hasOnlineOutcomeSource: false, hasOfflineOutcomeSource: false }),
      FIXED_NOW,
    );
    expect(result.knownGaps.some((gap) => gap.includes("outcome data source"))).toBe(true);
  });

  it("never presents a dollar amount, and only mentions MODEL_READY/COLLECTION_READY as the required negation, never a positive verdict", () => {
    const result = generatePlannerResult(intake({ channelCategoryIds: ["paid_search"] }), FIXED_NOW);
    const rendered = JSON.stringify(result);
    expect(rendered).not.toMatch(/\$\d/);
    const readinessMentions = rendered.match(/[^"]*(MODEL_READY|COLLECTION_READY)[^"]*/g) ?? [];
    for (const mention of readinessMentions) {
      expect(mention).toMatch(/not a/i);
    }
    expect(readinessMentions.length).toBeGreaterThan(0);
  });

  it("deduplicates providers that appear across multiple selected channels", () => {
    const result = generatePlannerResult(
      intake({ channelCategoryIds: ["paid_search", "paid_social"], providerIds: ["google_ads", "meta_ads"] }),
      FIXED_NOW,
    );
    const ids = result.likelySourceExports.map((p) => p.providerId);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
