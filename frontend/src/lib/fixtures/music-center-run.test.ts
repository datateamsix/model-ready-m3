import { describe, expect, it } from "vitest";
import {
  musicCenterDatasetAIssues,
  musicCenterDatasetARun,
  musicCenterDatasetATransformations,
} from "./music-center-run";

describe("Music Center Dataset A demo fixture", () => {
  it("matches the 5 seeded Phase 1 defects from datasets/music_center/expected_manifest.json", () => {
    expect(musicCenterDatasetAIssues).toHaveLength(5);
    expect(musicCenterDatasetAIssues.map((i) => i.issue_id)).toEqual([
      "MC-A-001",
      "MC-A-002",
      "MC-A-003",
      "MC-A-004",
      "MC-A-005",
    ]);
    expect(musicCenterDatasetAIssues.every((i) => i.remediation_class === "AUTO_SAFE")).toBe(true);
  });

  it("reports issue counts consistent with the run summary (5 detected, 5 resolved, 0 open)", () => {
    expect(musicCenterDatasetARun.detected_issue_count).toBe(5);
    expect(musicCenterDatasetARun.resolved_issue_count).toBe(5);
    expect(musicCenterDatasetARun.open_issue_count).toBe(0);
  });

  it("does not fabricate a transformation for the one issue with no documented tool name", () => {
    expect(musicCenterDatasetATransformations).toHaveLength(4);
    expect(musicCenterDatasetATransformations.find((t) => t.action_id === "action-MC-A-001")).toBeUndefined();
  });

  it("uses the real geos and period count from datasets/music_center/README.md", () => {
    expect(musicCenterDatasetARun.geos).toEqual(["CA", "TX", "FL", "NY"]);
    expect(musicCenterDatasetARun.period_count).toBe(131);
  });
});
