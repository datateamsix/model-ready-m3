import { describe, expect, it } from "vitest";
import { FixturePlanCatalogSource } from "./fixture-plan-catalog-source";

describe("FixturePlanCatalogSource", () => {
  const source = new FixturePlanCatalogSource();

  it("lists all four canonical plans with the real 0/1/10/50 project structure", async () => {
    const plans = await source.listPlans();
    const byId = Object.fromEntries(plans.map((p) => [p.planId, p]));
    expect(byId.planner.maxActiveProjects).toBe(0);
    expect(byId.project.maxActiveProjects).toBe(1);
    expect(byId.portfolio.maxActiveProjects).toBe(10);
    expect(byId.enterprise.maxActiveProjects).toBe(50);
  });

  it("never invents a dollar amount -- every plan's price is honestly null until REQ-012 lands", async () => {
    const plans = await source.listPlans();
    expect(plans.every((p) => p.monthlyPriceDisplay === null)).toBe(true);
  });
});
