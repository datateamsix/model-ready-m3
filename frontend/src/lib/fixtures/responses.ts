import type { StructuredResponse } from "@/types/response";

import blockedJson from "./response/blocked.json";
import datasetAAssessmentJson from "./response/dataset_a_assessment.json";
import datasetAFeasibilityJson from "./response/dataset_a_feasibility.json";
import datasetAParameterAdvisoryJson from "./response/dataset_a_parameter_advisory.json";
import datasetAScopeScenarioJson from "./response/dataset_a_scope_scenario.json";
import datasetASemanticInterviewJson from "./response/dataset_a_semantic_interview.json";
import domainViewJson from "./response/domain_view.json";
import guidedRemediationJson from "./response/guided_remediation.json";
import judgeModelReadyJson from "./response/judge_model_ready.json";
import learningJson from "./response/learning.json";
import modelReadyJson from "./response/model_ready.json";
import officialMeridianJson from "./response/official_meridian.json";

/**
 * Every export below is a real, schema-valid StructuredResponse produced
 * against app/response/contracts.py and checked into
 * tests/fixtures/response/. Copied verbatim in Task 9 — not authored here.
 */
export const modelReadyResponse = modelReadyJson as unknown as StructuredResponse;
export const judgeModelReadyResponse = judgeModelReadyJson as unknown as StructuredResponse;
export const officialMeridianResponse = officialMeridianJson as unknown as StructuredResponse;
export const learningResponse = learningJson as unknown as StructuredResponse;
export const domainViewResponse = domainViewJson as unknown as StructuredResponse;
export const datasetAAssessmentResponse = datasetAAssessmentJson as unknown as StructuredResponse;
export const datasetAFeasibilityResponse = datasetAFeasibilityJson as unknown as StructuredResponse;
export const datasetAParameterAdvisoryResponse =
  datasetAParameterAdvisoryJson as unknown as StructuredResponse;
export const datasetAScopeScenarioResponse =
  datasetAScopeScenarioJson as unknown as StructuredResponse;
export const datasetASemanticInterviewResponse =
  datasetASemanticInterviewJson as unknown as StructuredResponse;
export const guidedRemediationResponse = guidedRemediationJson as unknown as StructuredResponse;
export const blockedResponse = blockedJson as unknown as StructuredResponse;
