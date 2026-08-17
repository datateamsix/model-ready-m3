#!/usr/bin/env node
/**
 * M2-08: generates the Planner's provider snapshot from the curated backend
 * registry (`app/registry/providers/marketing_advertising_providers.v1.json`)
 * -- never hand-typed into a component (see the prompt pack's M2-08
 * standing rule). Only presentation-safe fields are extracted: no internal
 * field-mapping schemas, Meridian gap codes, or quirks notes, which are
 * Mission 1 execution detail, not customer-facing planning guidance.
 *
 * Run: `npm run planner:manifest:generate` from frontend/. Re-run whenever
 * the source registry changes; `npm run planner:manifest:check` fails CI if
 * the checked-in artifact has drifted from its source.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SOURCE_PATH = join(__dirname, "..", "..", "app", "registry", "providers", "marketing_advertising_providers.v1.json");
const OUTPUT_PATH = join(__dirname, "..", "src", "lib", "planner", "provider-snapshot.generated.json");

function generate() {
  const source = JSON.parse(readFileSync(SOURCE_PATH, "utf8"));

  const providers = source.providers.map((provider) => ({
    providerId: provider.provider_id,
    displayName: provider.display_name,
    category: provider.category,
    exportFormats: provider.export_formats,
  }));

  const output = {
    manifestVersion: source.version,
    sourceRetrievedAt: source.retrieved_at,
    generatedAt: new Date().toISOString(),
    generatedFrom: "app/registry/providers/marketing_advertising_providers.v1.json",
    providers,
  };

  return JSON.stringify(output, null, 2) + "\n";
}

const mode = process.argv[2] === "check" ? "check" : "generate";
const rendered = generate();

if (mode === "check") {
  let existing;
  try {
    existing = readFileSync(OUTPUT_PATH, "utf8");
  } catch {
    console.error(`Planner provider snapshot missing at ${OUTPUT_PATH}. Run planner:manifest:generate.`);
    process.exit(1);
  }
  // generatedAt is expected to differ run-to-run; compare everything else.
  const strip = (text) => text.replace(/"generatedAt":\s*"[^"]*"/, '"generatedAt":""');
  if (strip(existing) !== strip(rendered)) {
    console.error(
      "Planner provider snapshot is out of date with app/registry/providers/marketing_advertising_providers.v1.json. Run planner:manifest:generate.",
    );
    process.exit(1);
  }
  console.log("Planner provider snapshot is up to date.");
} else {
  writeFileSync(OUTPUT_PATH, rendered);
  console.log(`Wrote ${OUTPUT_PATH}`);
}
