import { PROVIDER_SNAPSHOT_SOURCE_RETRIEVED_AT, PROVIDER_SNAPSHOT_VERSION } from "./provider-snapshot";

/**
 * M2-08's Planner content manifest: channel categories and the data points
 * each requires. This is planning guidance content, not a readiness
 * authority -- it never asserts MODEL_READY/COLLECTION_READY, only what a
 * Meridian model typically needs collected for that channel type. Provider
 * data itself lives in provider-snapshot.ts (generated); this file is the
 * hand-authored planning logic layered on top of it.
 */
export const PLANNER_MANIFEST_VERSION = `planner-1.0.0+providers-${PROVIDER_SNAPSHOT_VERSION}`;
export const PLANNER_MANIFEST_SOURCE_TIMESTAMP = PROVIDER_SNAPSHOT_SOURCE_RETRIEVED_AT;

export interface ChannelCategory {
  id: string;
  label: string;
  /** Data points a Meridian model typically needs for this channel type,
   * in planning terms -- not a field-mapping spec. */
  requiredDataPoints: string[];
}

export const CHANNEL_CATEGORIES: ChannelCategory[] = [
  {
    id: "paid_search",
    label: "Paid Search",
    requiredDataPoints: ["Daily spend by campaign", "Impressions/clicks", "Geo (if regional)"],
  },
  {
    id: "paid_social",
    label: "Paid Social",
    requiredDataPoints: ["Daily spend by campaign", "Impressions/reach", "Creative/channel breakdown (optional)"],
  },
  {
    id: "dsp",
    label: "Programmatic / DSP",
    requiredDataPoints: ["Daily spend", "Impressions", "Reach & frequency (if available)"],
  },
  {
    id: "video_ctv",
    label: "Video / CTV",
    requiredDataPoints: ["Daily spend", "Impressions", "Reach & frequency (if available)"],
  },
  {
    id: "audio",
    label: "Audio",
    requiredDataPoints: ["Daily spend", "Impressions"],
  },
  {
    id: "retail_media",
    label: "Retail Media",
    requiredDataPoints: ["Daily spend by campaign", "Impressions/clicks", "Attributed sales (if available)"],
  },
  {
    id: "organic",
    label: "Organic / SEO",
    requiredDataPoints: ["Clicks/impressions by date", "No spend figure needed -- used as a control, not media"],
  },
  {
    id: "analytics",
    label: "Web/App Analytics",
    requiredDataPoints: ["Daily sessions/conversions", "Outcome event definition"],
  },
  {
    id: "attribution",
    label: "Mobile Attribution",
    requiredDataPoints: ["Daily installs/conversions by channel"],
  },
  {
    id: "commerce",
    label: "Commerce / Orders",
    requiredDataPoints: ["Daily orders/revenue", "Return/refund handling"],
  },
  {
    id: "crm",
    label: "CRM / Email",
    requiredDataPoints: ["Send/open/conversion volume by date"],
  },
  {
    id: "measurement",
    label: "Measurement / Macro",
    requiredDataPoints: ["Relevant macro/control series for your category"],
  },
];

export const CHANNEL_CATEGORY_MAP: Record<string, ChannelCategory> = Object.fromEntries(
  CHANNEL_CATEGORIES.map((category) => [category.id, category]),
);

export const BUSINESS_MODELS = [
  { id: "b2c_ecommerce", label: "B2C ecommerce" },
  { id: "b2b_saas", label: "B2B / SaaS" },
  { id: "retail_brick_and_mortar", label: "Retail (brick & mortar)" },
  { id: "marketplace", label: "Marketplace" },
  { id: "services", label: "Services" },
  { id: "other", label: "Other" },
] as const;

export const WAREHOUSE_LOCATIONS = [
  { id: "bigquery", label: "BigQuery" },
  { id: "snowflake", label: "Snowflake" },
  { id: "redshift", label: "Redshift" },
  { id: "spreadsheets_only", label: "Spreadsheets only" },
  { id: "none_yet", label: "No central location yet" },
  { id: "other", label: "Other" },
] as const;

export const EXPORT_STATUSES = [
  { id: "already_exporting", label: "Already exporting regularly" },
  { id: "can_export", label: "Can export, haven't set it up" },
  { id: "not_sure", label: "Not sure" },
] as const;

export const MERIDIAN_PREP_CHECKLIST_BASELINE = [
  "Daily or weekly grain for every channel, aligned to the same calendar",
  "A single, unambiguous outcome/KPI definition",
  "Spend and exposure (impressions/clicks) kept as separate columns, never pre-blended",
  "A consistent geography grain if modeling below national level",
];

/** Standard disclaimer required on every Planner result -- never omit or
 * reword this into something that sounds like a readiness certification. */
export const PLANNING_GUIDANCE_DISCLAIMER =
  "Planning guidance — not a MODEL_READY or COLLECTION_READY assessment.";
