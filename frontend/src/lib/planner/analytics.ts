/**
 * M2-08's Planner funnel events. No analytics vendor is wired into this
 * repo yet (documented gap, same discipline as ApiPreM3DataSource) -- this
 * module pins the typed event surface and a safe call-site shape now, so
 * swapping in a real sink later is a one-line change at `plannerAnalyticsSink`.
 *
 * The metadata type is deliberately narrow (only enum-like, non-free-text
 * fields) so a call site cannot accidentally forward business content --
 * there is no `details: string` escape hatch to misuse.
 */
export type PlannerAnalyticsEvent =
  | "planner_started"
  | "planner_section_completed"
  | "planner_result_viewed"
  | "planner_save_clicked"
  | "planner_signup_started"
  | "planner_checkout_started";

export interface PlannerAnalyticsMeta {
  sectionId?: string;
  channelCategoryCount?: number;
}

export type PlannerAnalyticsSink = (event: PlannerAnalyticsEvent, meta?: PlannerAnalyticsMeta) => void;

function defaultSink(event: PlannerAnalyticsEvent, meta?: PlannerAnalyticsMeta): void {
  if (process.env.NODE_ENV !== "production") {
    console.debug("[planner-analytics]", event, meta);
  }
}

let sink: PlannerAnalyticsSink = defaultSink;

export function setPlannerAnalyticsSink(nextSink: PlannerAnalyticsSink): void {
  sink = nextSink;
}

export function trackPlannerEvent(event: PlannerAnalyticsEvent, meta?: PlannerAnalyticsMeta): void {
  sink(event, meta);
}
