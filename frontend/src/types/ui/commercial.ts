/**
 * Frontend-only presentation model for Mission 2's commercial domain
 * (Projects, Datasets, Evaluations, plans, entitlements) -- see
 * frontend/src/types/ui/README.md for why this lives here and not in
 * frontend/src/types/generated/. None of these represent backend truth on
 * their own; components built from them take real data as props once
 * REQ-003/REQ-011/REQ-012 (docs/contracts/BACKEND_REQUESTS.md) exist.
 *
 * `PresentationStatus` is reused from @/types/response rather than a new
 * ad-hoc status type -- evaluation status is the same MODEL_READY-adjacent
 * vocabulary Mission 1 already renders via StatusBadge.
 */
import type { PresentationStatus } from "@/types/response";

export type PlanId = "planner" | "project" | "portfolio" | "enterprise";

export interface PlanSummary {
  planId: PlanId;
  displayName: string;
  /** null is reserved for a future truly-unlimited plan; none of the four
   * canonical plans (docs/superpowers/specs/2026-08-17-prem3-mission-2-commercial-model.md)
   * use it today. */
  maxActiveProjects: number | null;
}

export interface ProjectAllowanceSummary {
  activeProjectCount: number;
  maxActiveProjects: number;
}

export type ProjectStatus = "ACTIVE" | "ARCHIVED";

export interface ProjectSummary {
  workspaceId: string;
  name: string;
  status: ProjectStatus;
  datasetCount: number;
  /** Pre-formatted display string ("Updated 2 days ago"), not a raw
   * timestamp the component would need to format itself. */
  latestActivityLabel: string | null;
}

export interface DatasetSummary {
  datasetId: string;
  name: string;
  kpiLabel: string | null;
  grainLabel: string | null;
  latestEvaluationStatus: PresentationStatus | null;
  latestEvaluatedAtLabel: string | null;
  /** Real count of evaluations that exist for this Dataset -- never a
   * quota or "X of Y" figure. Re-evaluations are unlimited on every paid
   * plan (see the commercial model spec); there is no cap concept to
   * represent here. */
  evaluationCount: number;
}

export interface EvaluationHistoryEntry {
  runId: string;
  status: PresentationStatus;
  evaluatedAtLabel: string;
}

export type PlanCtaKind = "start_planner" | "start_project" | "contact_sales";

/**
 * The public plan catalog (M2-05). Field list matches what REQ-012
 * (docs/contracts/BACKEND_REQUESTS.md) asks the backend to eventually
 * serve exactly -- so the day that endpoint exists, only the adapter
 * (src/lib/adapters/plan-catalog-source.ts) needs to change, not this
 * type or any component built against it.
 */
export interface PlanCatalogEntry {
  planId: PlanId;
  displayName: string;
  /** null means "not yet configured" -- rendered as an honest placeholder,
   * never a plausible-looking invented number. Real values come only from
   * REQ-012's backend plan catalog once it exists. */
  monthlyPriceDisplay: string | null;
  billingInterval: "monthly";
  maxActiveProjects: number;
  ctaKind: PlanCtaKind;
  ctaLabel: string;
  stripeCheckoutAvailable: boolean;
  featureSummary: string[];
}
