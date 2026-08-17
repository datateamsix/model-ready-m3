import { describe, expect, it } from "vitest";
import { FixturePreM3DataSource } from "./fixture-data-source";

describe("FixturePreM3DataSource", () => {
  const dataSource = new FixturePreM3DataSource();

  it("lists the Music Center Dataset A demo run", async () => {
    const runs = await dataSource.listRuns();
    expect(runs.map((r) => r.run_id)).toContain("music-center-dataset-a-demo");
  });

  it("returns null for a run that does not exist rather than throwing", async () => {
    const run = await dataSource.getRun("does-not-exist");
    expect(run).toBeNull();
  });

  it("returns the full response set for the Music Center run", async () => {
    const responses = await dataSource.getRunResponses("music-center-dataset-a-demo");
    expect(responses.modelReady?.response_type).toBe("MODEL_READY");
    expect(responses.officialMeridian?.response_type).toBe("OFFICIAL_MERIDIAN_EDA");
    expect(responses.learning?.status).toBe("COMPLETE");
    expect(responses.domainView?.response_type).toBe("DOMAIN_VIEW");
  });

  it("returns the real DOMAIN_VIEW with 0 promoted lessons", async () => {
    const domainView = await dataSource.getDomainView();
    expect(domainView.promoted_lesson_count).toBe(0);
  });

  it("returns the experience bundle for the Music Center run and null for an unknown run", async () => {
    const known = await dataSource.getExperience("music-center-dataset-a-demo");
    expect(known?.episode.terminal_outcome).toBe("MODEL_READY");

    const unknown = await dataSource.getExperience("does-not-exist");
    expect(unknown).toBeNull();
  });
});
