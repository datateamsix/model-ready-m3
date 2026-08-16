import { describe, expect, it } from "vitest";
import type { StructuredResponse } from "./response";

function buildMinimalResponse(): StructuredResponse {
  return {
    response_type: "LEARNING",
    title: "t",
    summary: "s",
    status: "COMPLETE",
    sections: [],
    metrics: [],
    findings: [],
    insights: [],
    actions: [],
    questions: [],
    scenarios: [],
    feasibility_rows: [],
    official_meridian: [],
    authority: [],
    sources: [],
    proof: {
      receipts: [],
      fingerprints: {},
      bigquery_endpoint: null,
      rule_ids: [],
      source_refs: [],
      artifact_uris: [],
      official_meridian_raw: [],
    },
    technical_details: {
      run_id: null,
      fingerprints: {},
      registry_ids: [],
      artifact_hashes: {},
      storage_paths: [],
      tool_names: [],
      raw_enums: {},
      raw_error: null,
    },
    product_behaviors: [],
    disclosure: {
      default_level: "SUMMARY",
      summary_finding_ids: [],
      additional_finding_count: 0,
      view_all_available: false,
      question_display_limit: 5,
    },
    qa_hooks: null,
    gate_evidence: null,
    blocked_reason: null,
    retry_condition: null,
    consistency_group: null,
    architecture_version: "1.0.0",
  };
}

describe("StructuredResponse contract shape", () => {
  it("accepts a minimal valid literal", () => {
    const response = buildMinimalResponse();
    expect(response.response_type).toBe("LEARNING");
  });
});
