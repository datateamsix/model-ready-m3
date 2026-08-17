import { describe, expect, it } from "vitest";
import {
  blockedResponse,
  datasetAAssessmentResponse,
  datasetAFeasibilityResponse,
  datasetAParameterAdvisoryResponse,
  datasetAScopeScenarioResponse,
  datasetASemanticInterviewResponse,
  domainViewResponse,
  guidedRemediationResponse,
  judgeModelReadyResponse,
  learningResponse,
  modelReadyResponse,
  officialMeridianResponse,
} from "./responses";

describe("real backend response fixtures", () => {
  it("preserves the real response_type for each fixture", () => {
    expect(modelReadyResponse.response_type).toBe("MODEL_READY");
    expect(judgeModelReadyResponse.response_type).toBe("JUDGE_DEMO");
    expect(officialMeridianResponse.response_type).toBe("OFFICIAL_MERIDIAN_EDA");
    expect(learningResponse.response_type).toBe("LEARNING");
    expect(domainViewResponse.response_type).toBe("DOMAIN_VIEW");
    expect(datasetAAssessmentResponse.response_type).toBeTruthy();
    expect(datasetAFeasibilityResponse.response_type).toBeTruthy();
    expect(datasetAParameterAdvisoryResponse.response_type).toBeTruthy();
    expect(datasetAScopeScenarioResponse.response_type).toBeTruthy();
    expect(datasetASemanticInterviewResponse.response_type).toBeTruthy();
    expect(guidedRemediationResponse.response_type).toBeTruthy();
    expect(blockedResponse.response_type).toBe("BLOCKED");
  });

  it("keeps the real, un-fabricated zero-learning fact in the learning fixture", () => {
    const metric = learningResponse.metrics.find((m) => m.metric_id === "promoted-lessons");
    expect(metric?.value).toBe(0);
  });

  it("keeps official Meridian severity separate from PreM3 interpretation", () => {
    const finding = officialMeridianResponse.findings[0];
    expect(finding.official_severity).toBe("ATTENTION");
    expect(finding.prem3_interpretation).not.toBe(finding.official_finding_text);
  });
});
