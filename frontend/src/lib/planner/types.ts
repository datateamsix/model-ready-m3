export type BusinessModelId =
  | "b2c_ecommerce"
  | "b2b_saas"
  | "retail_brick_and_mortar"
  | "marketplace"
  | "services"
  | "other";

export type WarehouseLocationId = "bigquery" | "snowflake" | "redshift" | "spreadsheets_only" | "none_yet" | "other";

export type ExportStatusId = "already_exporting" | "can_export" | "not_sure";

/**
 * The anonymous Planner's intake state. Free-text fields (industryLabel,
 * desiredUseCase) may carry real business content -- never forward these to
 * analytics (see analytics.ts's PLANNER_ANALYTICS_EVENTS, which are
 * metadata-only).
 */
export interface PlannerIntake {
  businessModel: BusinessModelId | null;
  industryLabel: string;
  primaryOutcome: string;
  markets: string[];
  historyLengthMonths: number | null;
  channelCategoryIds: string[];
  providerIds: string[];
  hasOnlineOutcomeSource: boolean | null;
  hasOfflineOutcomeSource: boolean | null;
  warehouseLocation: WarehouseLocationId | null;
  exportStatus: ExportStatusId | null;
  hasPromoPricingSeasonality: boolean | null;
  hasFirstPartyCrm: boolean | null;
  desiredUseCase: string;
}

export const EMPTY_PLANNER_INTAKE: PlannerIntake = {
  businessModel: null,
  industryLabel: "",
  primaryOutcome: "",
  markets: [],
  historyLengthMonths: null,
  channelCategoryIds: [],
  providerIds: [],
  hasOnlineOutcomeSource: null,
  hasOfflineOutcomeSource: null,
  warehouseLocation: null,
  exportStatus: null,
  hasPromoPricingSeasonality: null,
  hasFirstPartyCrm: null,
  desiredUseCase: "",
};

export interface DataAcquisitionMapEntry {
  channelCategoryId: string;
  channelLabel: string;
  requiredDataPoints: string[];
  likelyProviders: { providerId: string; displayName: string; exportFormats: string[] }[];
}

export interface LikelySourceExport {
  providerId: string;
  displayName: string;
  exportFormats: string[];
}

export interface PlannerResult {
  manifestVersion: string;
  generatedAt: string;
  blueprint: {
    title: string;
    summary: string;
    highlights: string[];
  };
  dataAcquisitionMap: DataAcquisitionMapEntry[];
  likelySourceExports: LikelySourceExport[];
  meridianPrepChecklist: string[];
  knownGaps: string[];
  nextActions: string[];
  disclaimer: string;
}
