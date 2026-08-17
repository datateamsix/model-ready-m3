import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

/**
 * M2-06 security requirement: "no Clerk secret in client bundle." This is a
 * static regression guard, not a build-output scan (see
 * .github/workflows/frontend.yml for the build-output companion check) --
 * it catches the source-level mistake of a "use client" file importing
 * CLERK_SECRET_KEY before it ever reaches a bundle.
 */

const SRC_ROOT = join(__dirname, "..", "..");

function collectSourceFiles(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stats = statSync(full);
    if (stats.isDirectory()) {
      collectSourceFiles(full, out);
    } else if (/\.(ts|tsx)$/.test(entry) && !entry.endsWith(".test.ts") && !entry.endsWith(".test.tsx")) {
      out.push(full);
    }
  }
  return out;
}

describe("Clerk secret boundary", () => {
  it("never references CLERK_SECRET_KEY from a 'use client' file", () => {
    const offenders: string[] = [];
    for (const file of collectSourceFiles(SRC_ROOT)) {
      const contents = readFileSync(file, "utf8");
      const isClientFile = /^\s*["']use client["']/.test(contents);
      if (isClientFile && contents.includes("CLERK_SECRET_KEY")) {
        offenders.push(file);
      }
    }
    expect(offenders).toEqual([]);
  });

  it("keeps PREM3_API_BASE_URL server-only -- never NEXT_PUBLIC_-prefixed", () => {
    const offenders: string[] = [];
    for (const file of collectSourceFiles(SRC_ROOT)) {
      const contents = readFileSync(file, "utf8");
      if (contents.includes("NEXT_PUBLIC_PREM3_API_BASE_URL")) {
        offenders.push(file);
      }
    }
    expect(offenders).toEqual([]);
  });
});
