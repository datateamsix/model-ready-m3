import { planCatalogFixture } from "@/lib/fixtures/plan-catalog";
import type { PlanCatalogEntry } from "@/types/ui/commercial";
import type { PlanCatalogSource } from "./plan-catalog-source";

/**
 * Reads from src/lib/fixtures/plan-catalog.ts. This is the only
 * PlanCatalogSource Mission 2 ships until REQ-012's backend endpoint
 * exists -- see plan-catalog-source.ts for the swap plan.
 */
export class FixturePlanCatalogSource implements PlanCatalogSource {
  async listPlans(): Promise<PlanCatalogEntry[]> {
    return planCatalogFixture;
  }
}

export const planCatalogSource: PlanCatalogSource = new FixturePlanCatalogSource();
