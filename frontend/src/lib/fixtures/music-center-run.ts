import type { Issue, RunSummary, Transformation } from "@/types/run";

/**
 * UI_DEMO_FIXTURE
 *
 * Composed for frontend visual development. There is no live PreM3 backend
 * in Mission 1, so this is not a captured real run — it is assembled from
 * verified facts in datasets/music_center/expected_manifest.json and
 * datasets/music_center/README.md (5 seeded Phase 1 defects, all
 * AUTO_SAFE, real rule families; 131 weekly periods; geos CA/TX/FL/NY).
 *
 * Sourced fields: issue rule_id/title/remediation_class/evidence, geos,
 * grain, period_count, detected/resolved/open issue counts (5/5/0, matching
 * the README's "Proven: autonomous Dataset A preparation" claim).
 *
 * Illustrative (not sourced from a specific backend record) fields:
 * run_id, created_at/updated_at, issue_id/action_id string formatting,
 * and Issue.severity (the source manifest records remediation_class and
 * rule_family but not severity). None of these illustrative fields are
 * MODEL_READY, Meridian, or learning claims.
 */

export const musicCenterDatasetAIssues: Issue[] = [
  {
    issue_id: "MC-A-001",
    rule_id: "MR-010",
    severity: "WARN",
    title: "Duplicate Google Ads campaign row",
    evidence: { date: "2025-03-12", geo: "TX", campaign: "Search | Nonbrand", file: "google_ads_daily.csv" },
    remediation_class: "AUTO_SAFE",
    proposed_action: { action: "drop_exact_duplicate_row" },
    status: "RESOLVED",
    resolution_action_ids: ["action-MC-A-001"],
    resolved_at: null,
    resolution_evidence: {},
  },
  {
    issue_id: "MC-A-002",
    rule_id: "MR-001",
    severity: "WARN",
    title: "Date format mismatch across sources",
    evidence: { files: ["google_ads_daily.csv", "meta_ads_weekly.csv"], formats: ["YYYY-MM-DD", "MM/DD/YYYY"] },
    remediation_class: "AUTO_SAFE",
    proposed_action: { action: "normalize_dates", target_format: "YYYY-MM-DD" },
    status: "RESOLVED",
    resolution_action_ids: ["action-MC-A-002"],
    resolved_at: null,
    resolution_evidence: {},
  },
  {
    issue_id: "MC-A-003",
    rule_id: "MR-003",
    severity: "WARN",
    title: "Daily vs. weekly grain mismatch",
    evidence: { file: "google_ads_daily.csv", source_grain: "daily", target_grain: "weekly" },
    remediation_class: "AUTO_SAFE",
    proposed_action: { action: "aggregate_to_week" },
    status: "RESOLVED",
    resolution_action_ids: ["action-MC-A-003"],
    resolved_at: null,
    resolution_evidence: {},
  },
  {
    issue_id: "MC-A-004",
    rule_id: "MR-017",
    severity: "WARN",
    title: "Currency-formatted spend field",
    evidence: { file: "meta_ads_weekly.csv", field: "amount_spent", pattern: "$#,##0.00" },
    remediation_class: "AUTO_SAFE",
    proposed_action: { action: "normalize_numeric_values", field: "amount_spent" },
    status: "RESOLVED",
    resolution_action_ids: ["action-MC-A-004"],
    resolved_at: null,
    resolution_evidence: {},
  },
  {
    issue_id: "MC-A-005",
    rule_id: "MR-009",
    severity: "WARN",
    title: "Inconsistent Meta channel labels",
    evidence: {
      file: "meta_ads_weekly.csv",
      field: "channel",
      observed_values: ["Meta", "Paid Social", "paid_social"],
      canonical_channel: "paid_social",
    },
    remediation_class: "AUTO_SAFE",
    proposed_action: { action: "apply_mapping", target: "paid_social" },
    status: "RESOLVED",
    resolution_action_ids: ["action-MC-A-005"],
    resolved_at: null,
    resolution_evidence: {},
  },
];

/**
 * Only the 4 issues with a deterministic tool name already documented in
 * docs/context/02_SYSTEM_ARCHITECTURE.md's tool catalog get a
 * Transformation entry here. MC-A-001's exact duplicate-removal tool name
 * is not present in that catalog (only the detector detect_duplicates is),
 * so it is intentionally left out rather than guessed — the Issue record
 * above still shows it as RESOLVED.
 */
export const musicCenterDatasetATransformations: Transformation[] = [
  {
    action_id: "action-MC-A-002",
    tool: "normalize_dates",
    source_fields: ["date", "week_start"],
    target_fields: ["date"],
    parameters: { target_format: "YYYY-MM-DD" },
    reason: "Meta Ads weekly export used MM/DD/YYYY while Google Ads used ISO dates.",
    lesson_ids: [],
    status: "APPLIED",
  },
  {
    action_id: "action-MC-A-003",
    tool: "aggregate_to_week",
    source_fields: ["date"],
    target_fields: ["week_start"],
    parameters: { source_grain: "daily", target_grain: "weekly" },
    reason: "Google Ads exported daily rows against a weekly KPI/control grain.",
    lesson_ids: [],
    status: "APPLIED",
  },
  {
    action_id: "action-MC-A-004",
    tool: "normalize_numeric_values",
    source_fields: ["amount_spent"],
    target_fields: ["media_spend"],
    parameters: { strip_currency_formatting: true },
    reason: "amount_spent was encoded as currency strings such as \"$1,234.56\".",
    lesson_ids: [],
    status: "APPLIED",
  },
  {
    action_id: "action-MC-A-005",
    tool: "apply_mapping",
    source_fields: ["channel"],
    target_fields: ["channel"],
    parameters: { canonical_value: "paid_social", observed_values: ["Meta", "Paid Social", "paid_social"] },
    reason: "Meta channel label was inconsistent across rows.",
    lesson_ids: [],
    status: "APPLIED",
  },
];

export const musicCenterDatasetARun: RunSummary = {
  run_id: "music-center-dataset-a-demo",
  business: "Music Center",
  dataset_label: "Dataset A — Phase 1 golden pre-modeling path",
  stage: "COMPLETE",
  failed: false,
  created_at: "2026-08-16T09:00:00Z",
  updated_at: "2026-08-16T09:14:00Z",
  detected_issue_count: 5,
  resolved_issue_count: 5,
  open_issue_count: 0,
  geos: ["CA", "TX", "FL", "NY"],
  grain: "weekly",
  period_count: 131,
};
