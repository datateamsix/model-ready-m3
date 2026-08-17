import { describe, expect, it } from "vitest";
import type { DomainView } from "./domain-view";

function buildMinimalDomainView(): DomainView {
  return {
    domain_view_version: "1.0.0",
    generated_at: "2026-08-16T00:00:00Z",
    source_versions: {
      intelligence_version: "2.0.0",
      product_context_version: "2.0",
      mmm_boot_context_version: "1.0",
      rule_registry_version: "0.1.0",
      intelligence_registry_version: "1.0.0",
      source_verification_date: "2026-08-16",
      meridian_worker_pin: "google-meridian==1.8.0",
    },
    promoted_lesson_set_version: "0.0.0",
    promoted_lesson_count: 0,
    content_fingerprint: "abc123",
    previous_domain_view_version: null,
    status: "ACTIVE",
    claims: [],
  };
}

describe("DomainView contract shape", () => {
  it("represents an honest zero-promoted-lesson state", () => {
    const view = buildMinimalDomainView();
    expect(view.promoted_lesson_count).toBe(0);
  });
});
