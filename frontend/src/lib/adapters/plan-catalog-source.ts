import type { PlanCatalogEntry } from "@/types/ui/commercial";

/**
 * The only data boundary /pricing (and anything else that needs plan
 * catalog data) is allowed to depend on -- mirrors PreM3DataSource's
 * pattern (src/lib/adapters/data-source.ts). A component that needs plan
 * data takes it as a prop; a page resolves that prop through this
 * interface. Swapping FixturePlanCatalogSource for a real
 * ApiPlanCatalogSource once REQ-012 exists is a one-line change at
 * planCatalogSource's definition -- no component or page changes needed.
 */
export interface PlanCatalogSource {
  listPlans(): Promise<PlanCatalogEntry[]>;
}
