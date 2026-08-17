import generated from "./provider-snapshot.generated.json";

/**
 * Typed access to the generated provider snapshot (see
 * scripts/generate-planner-manifest.mjs). Never hand-type provider entries
 * here -- add/edit the source registry
 * (app/registry/providers/marketing_advertising_providers.v1.json) and
 * regenerate instead.
 */
export interface PlannerProviderSnapshot {
  providerId: string;
  displayName: string;
  category: string;
  exportFormats: string[];
}

export const PROVIDER_SNAPSHOT_VERSION: string = generated.manifestVersion;
export const PROVIDER_SNAPSHOT_SOURCE_RETRIEVED_AT: string = generated.sourceRetrievedAt;
export const PROVIDER_SNAPSHOT: PlannerProviderSnapshot[] = generated.providers;

export function providersInCategory(categoryId: string): PlannerProviderSnapshot[] {
  return PROVIDER_SNAPSHOT.filter((provider) => provider.category === categoryId);
}

export function findProviders(providerIds: string[]): PlannerProviderSnapshot[] {
  const idSet = new Set(providerIds);
  return PROVIDER_SNAPSHOT.filter((provider) => idSet.has(provider.providerId));
}
