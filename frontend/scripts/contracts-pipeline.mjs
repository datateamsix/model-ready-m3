#!/usr/bin/env node
/**
 * Shared entry point for the contracts:check / contracts:generate /
 * api:generate npm scripts (Mission 2 M2-02). All three currently do the
 * same thing -- confirm whether contracts/openapi.yaml exists yet -- because
 * none of them can do real work until it does (blocked on
 * docs/contracts/BACKEND_REQUESTS.md's REQ-002). See contracts/README.md
 * for the intended pipeline once that contract lands.
 *
 * Exits 0 either way: a missing upstream contract the frontend track
 * doesn't own is not the same signal as catching real drift in an existing
 * one, and CI should not go red over it.
 */
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const openapiPath = resolve(__dirname, "..", "..", "contracts", "openapi.yaml");

const STEP_LABELS = {
  check: "contracts:check",
  generate: "contracts:generate",
  api: "api:generate",
};

const step = process.argv[2] ?? "check";
const label = STEP_LABELS[step] ?? step;

if (!existsSync(openapiPath)) {
  console.warn(
    `[${label}] contracts/openapi.yaml does not exist yet -- blocked on ` +
      `docs/contracts/BACKEND_REQUESTS.md's REQ-002 (OpenAPI freeze). ` +
      `Informational no-op, not a failure -- see contracts/README.md.`,
  );
  process.exit(0);
}

console.log(
  `[${label}] contracts/openapi.yaml found, but real generation/drift-checking ` +
    `is not yet wired up -- see contracts/README.md for the intended pipeline.`,
);
process.exit(0);
