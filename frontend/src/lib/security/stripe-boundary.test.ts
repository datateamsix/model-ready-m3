import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * M2-07 security requirements: no Stripe secret-key or webhook handling in
 * frontend code, no custom card form, and no direct Stripe SDK usage --
 * every checkout/portal flow goes through prem3-api via the BFF
 * (src/lib/server/prem3-api-client.ts). This is a static regression guard,
 * not a one-time finding.
 */

const PACKAGE_JSON = JSON.parse(readFileSync(join(__dirname, "..", "..", "..", "package.json"), "utf8"));

describe("Stripe boundary", () => {
  it("has no Stripe SDK as a dependency -- checkout/portal creation is prem3-api's job, not the frontend's", () => {
    const deps = { ...PACKAGE_JSON.dependencies, ...PACKAGE_JSON.devDependencies };
    const stripeDeps = Object.keys(deps).filter((name) => name.toLowerCase().includes("stripe"));
    expect(stripeDeps).toEqual([]);
  });
});
