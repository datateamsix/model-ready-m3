import {
  BUSINESS_MODELS,
  CHANNEL_CATEGORY_MAP,
  MERIDIAN_PREP_CHECKLIST_BASELINE,
  PLANNER_MANIFEST_VERSION,
  PLANNING_GUIDANCE_DISCLAIMER,
} from "./manifest";
import { findProviders, providersInCategory } from "./provider-snapshot";
import type { DataAcquisitionMapEntry, PlannerIntake, PlannerResult } from "./types";

const MAX_PROVIDERS_PER_CHANNEL = 4;

/**
 * Deterministic: same PlannerIntake always produces the same PlannerResult
 * (aside from `generatedAt`). No PreM3/GCP call, no randomness, no AI --
 * this is a rules engine over the manifest, matching M2-08's "deterministic
 * planning utility, not an AI chat experience" requirement.
 */
export function generatePlannerResult(intake: PlannerIntake, now: Date = new Date()): PlannerResult {
  const dataAcquisitionMap = buildDataAcquisitionMap(intake);
  const likelySourceExports = dedupeProviders(dataAcquisitionMap.flatMap((entry) => entry.likelyProviders));
  const knownGaps = buildKnownGaps(intake);
  const meridianPrepChecklist = buildChecklist(intake);

  return {
    manifestVersion: PLANNER_MANIFEST_VERSION,
    generatedAt: now.toISOString(),
    blueprint: buildBlueprint(intake),
    dataAcquisitionMap,
    likelySourceExports,
    meridianPrepChecklist,
    knownGaps,
    nextActions: buildNextActions(intake, knownGaps),
    disclaimer: PLANNING_GUIDANCE_DISCLAIMER,
  };
}

function businessModelLabel(id: PlannerIntake["businessModel"]): string {
  return BUSINESS_MODELS.find((model) => model.id === id)?.label ?? "your business";
}

function buildBlueprint(intake: PlannerIntake): PlannerResult["blueprint"] {
  const modelLabel = businessModelLabel(intake.businessModel);
  const outcome = intake.primaryOutcome.trim() || "your primary outcome";
  const marketsLabel = intake.markets.length > 0 ? intake.markets.join(", ") : "your markets";
  const historyLabel =
    intake.historyLengthMonths != null
      ? `${intake.historyLengthMonths} month${intake.historyLengthMonths === 1 ? "" : "s"} of marketing history`
      : "an unspecified amount of marketing history";

  return {
    title: "Your MMM Project Blueprint",
    summary: `A ${modelLabel} planning to model ${outcome} across ${marketsLabel}, with ${historyLabel} available.`,
    highlights: [
      `${intake.channelCategoryIds.length} channel ${intake.channelCategoryIds.length === 1 ? "category" : "categories"} in scope`,
      `${intake.providerIds.length} specific platform${intake.providerIds.length === 1 ? "" : "s"} identified`,
    ],
  };
}

function buildDataAcquisitionMap(intake: PlannerIntake): DataAcquisitionMapEntry[] {
  return intake.channelCategoryIds
    .map((categoryId) => CHANNEL_CATEGORY_MAP[categoryId])
    .filter((category): category is NonNullable<typeof category> => category != null)
    .map((category) => {
      const selectedInCategory = findProviders(intake.providerIds).filter((p) => p.category === category.id);
      const likelyProviders =
        selectedInCategory.length > 0
          ? selectedInCategory
          : providersInCategory(category.id).slice(0, MAX_PROVIDERS_PER_CHANNEL);

      return {
        channelCategoryId: category.id,
        channelLabel: category.label,
        requiredDataPoints: category.requiredDataPoints,
        likelyProviders: likelyProviders.map((p) => ({
          providerId: p.providerId,
          displayName: p.displayName,
          exportFormats: p.exportFormats,
        })),
      };
    });
}

function dedupeProviders(
  providers: PlannerResult["likelySourceExports"],
): PlannerResult["likelySourceExports"] {
  const seen = new Map<string, PlannerResult["likelySourceExports"][number]>();
  for (const provider of providers) {
    if (!seen.has(provider.providerId)) {
      seen.set(provider.providerId, provider);
    }
  }
  return [...seen.values()];
}

function buildKnownGaps(intake: PlannerIntake): string[] {
  const gaps: string[] = [];

  if (intake.channelCategoryIds.length === 0) {
    gaps.push("No channel categories selected yet -- the data acquisition map will stay empty until you add some.");
  }
  if (intake.providerIds.length === 0 && intake.channelCategoryIds.length > 0) {
    gaps.push("No specific platforms identified -- shown providers are category defaults, not confirmed sources.");
  }
  if (intake.historyLengthMonths != null && intake.historyLengthMonths < 6) {
    gaps.push("Under 6 months of marketing history is often too little for a stable Meridian fit.");
  }
  if (intake.historyLengthMonths == null) {
    gaps.push("Marketing history length wasn't provided -- this materially affects model feasibility.");
  }
  if (intake.warehouseLocation === "spreadsheets_only" || intake.warehouseLocation === "none_yet") {
    gaps.push("No central warehouse yet -- exports will need to be consolidated manually or via a new pipeline.");
  }
  if (intake.exportStatus === "not_sure") {
    gaps.push("Export access isn't confirmed for one or more platforms -- verify before collection.");
  }
  if (intake.hasPromoPricingSeasonality === false) {
    gaps.push("No promotion/pricing/seasonality data yet -- these are important control variables.");
  }
  if (intake.hasOnlineOutcomeSource === false && intake.hasOfflineOutcomeSource === false) {
    gaps.push("No outcome data source identified yet -- this is required before any modeling can start.");
  }

  return gaps;
}

function buildChecklist(intake: PlannerIntake): string[] {
  const checklist = [...MERIDIAN_PREP_CHECKLIST_BASELINE];

  if (intake.hasFirstPartyCrm) {
    checklist.push("First-party/CRM data available -- useful as an additional control or outcome cross-check");
  }
  if (intake.hasPromoPricingSeasonality) {
    checklist.push("Promotion/pricing/seasonality data available -- plan to include as controls");
  }

  return checklist;
}

function buildNextActions(intake: PlannerIntake, knownGaps: string[]): string[] {
  const actions: string[] = [];

  if (intake.channelCategoryIds.length === 0) {
    actions.push("Come back and select the channels you actually spend on.");
  }
  if (knownGaps.some((gap) => gap.includes("outcome data source"))) {
    actions.push("Identify where your primary outcome metric is measured (analytics, CRM, or POS/commerce system).");
  }
  if (knownGaps.some((gap) => gap.includes("warehouse"))) {
    actions.push("Pick a central location (e.g. BigQuery) to land exports before collection starts.");
  }
  actions.push("Confirm export access for each platform above (API or scheduled file export).");
  actions.push("Continue with PreM3 to turn this brief into a real MMM Project once you're ready to collect data.");

  return actions;
}
