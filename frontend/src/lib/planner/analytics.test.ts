import { afterEach, describe, expect, it, vi } from "vitest";
import { setPlannerAnalyticsSink, trackPlannerEvent } from "./analytics";

describe("Planner analytics", () => {
  afterEach(() => {
    setPlannerAnalyticsSink(() => {});
  });

  it("dispatches events to the configured sink with only typed, non-free-text metadata", () => {
    const sink = vi.fn();
    setPlannerAnalyticsSink(sink);

    trackPlannerEvent("planner_section_completed", { sectionId: "channels", channelCategoryCount: 3 });

    expect(sink).toHaveBeenCalledWith("planner_section_completed", { sectionId: "channels", channelCategoryCount: 3 });
  });

  it("supports every documented funnel event name", () => {
    const sink = vi.fn();
    setPlannerAnalyticsSink(sink);
    const events = [
      "planner_started",
      "planner_section_completed",
      "planner_result_viewed",
      "planner_save_clicked",
      "planner_signup_started",
      "planner_checkout_started",
    ] as const;

    events.forEach((event) => trackPlannerEvent(event));

    expect(sink).toHaveBeenCalledTimes(events.length);
  });
});
