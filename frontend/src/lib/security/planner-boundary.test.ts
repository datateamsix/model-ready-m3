import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * M2-08 requirement: no PreM3/GCP runtime request during anonymous
 * planning/result generation. The manifest/decision-engine/storage/
 * analytics modules that make up that path must never import `fetch`-based
 * backend clients -- only planner-conversion-cta.tsx (a distinct, later
 * phase, shown only after a result exists) is allowed to call the BFF.
 */
const PLANNER_LIB_DIR = join(__dirname, "..", "planner");
const PLANNING_PHASE_FILES = [
  "decision-engine.ts",
  "manifest.ts",
  "provider-snapshot.ts",
  "storage.ts",
  "types.ts",
  "analytics.ts",
];

describe("Planner network boundary", () => {
  it("the planning/result-generation modules never import a prem3-api client or call fetch", () => {
    for (const file of PLANNING_PHASE_FILES) {
      const contents = readFileSync(join(PLANNER_LIB_DIR, file), "utf8");
      expect(contents, `${file} must not import prem3-api-client`).not.toMatch(/prem3-api-client/);
      expect(contents, `${file} must not import an api-*-source adapter`).not.toMatch(/adapters\/api-/);
      expect(contents, `${file} must not call fetch()`).not.toMatch(/\bfetch\(/);
    }
  });
});
