import { describe, expect, it } from "vitest";
import { domainViewV1 } from "./domain-view";
import { musicCenterExperienceBundle } from "./experience";

describe("real DOMAIN_VIEW artifact", () => {
  it("is the real v1.0.0 view with 0 promoted lessons and 35 claims", () => {
    expect(domainViewV1.domain_view_version).toBe("1.0.0");
    expect(domainViewV1.promoted_lesson_count).toBe(0);
    expect(domainViewV1.claims).toHaveLength(35);
  });
});

describe("Music Center experience bundle (UI_DEMO_FIXTURE)", () => {
  it("links the episode to the real Music Center Dataset A run", () => {
    expect(musicCenterExperienceBundle.episode.run_id).toBe("music-center-dataset-a-demo");
    expect(musicCenterExperienceBundle.episode.terminal_outcome).toBe("MODEL_READY");
  });

  it("keeps the reflection structurally unable to carry operational authority", () => {
    expect(musicCenterExperienceBundle.reflection?.operational_authority).toBe(false);
  });

  it("does not fabricate a promotion receipt or an experience application", () => {
    expect(musicCenterExperienceBundle.promotionReceipt).toBeNull();
    expect(musicCenterExperienceBundle.application).toBeNull();
  });
});
