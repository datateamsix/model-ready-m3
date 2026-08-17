import { describe, expect, it } from "vitest";
import { isTestEnvironmentReady } from "./env-check";

describe("vitest + jsdom harness", () => {
  it("runs in a jsdom window environment", () => {
    expect(isTestEnvironmentReady()).toBe(true);
  });
});
