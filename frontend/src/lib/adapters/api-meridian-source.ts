import type { MeridianSource } from "./meridian-source";
import type { MeridianIntegrationSummary } from "@/types/ui/commercial";
import type { PresentationStatus } from "@/types/response";
import { callPreM3Api, mapPreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * REQ-017 is a newly filed gap (M2-14, 2026-08-18) -- no backend field or
 * endpoint covers this surface at all yet. This assumed shape is recorded
 * in docs/contracts/BACKEND_REQUESTS.md's REQ-017 entry so nothing here is
 * invented silently: the frontend is wired against this exact assumption
 * and fails loudly with the typed 503 PREM3_API_NOT_CONFIGURED pattern
 * until it's real. Reuses PresentationStatus for integration_checks'
 * per-check status rather than a parallel vocabulary.
 */
interface MeridianIntegrationResponse {
  workspace_id: string;
  eda_report_status: string | null;
  eda_report_url: string | null;
  model_ready_data_location_label: string | null;
  bigquery_publish_verified: boolean | null;
  required_artifacts: string[];
  integration_checks: { label: string; status: PresentationStatus }[];
  readiness_receipt_label: string | null;
  next_approved_modeling_action: string | null;
}

function toMeridianIntegrationSummary(response: MeridianIntegrationResponse): MeridianIntegrationSummary {
  return {
    workspaceId: response.workspace_id,
    edaReportStatus: response.eda_report_status,
    edaReportUrl: response.eda_report_url,
    modelReadyDataLocationLabel: response.model_ready_data_location_label,
    bigQueryPublishVerified: response.bigquery_publish_verified,
    requiredArtifacts: response.required_artifacts,
    integrationChecks: response.integration_checks,
    readinessReceiptLabel: response.readiness_receipt_label,
    nextApprovedModelingAction: response.next_approved_modeling_action,
  };
}

/**
 * The real implementation of MeridianSource -- calls the assumed
 * `GET /v1/workspaces/{workspace_id}/meridian-integration` (REQ-017, not
 * started). Fails loudly with a typed error (never a fabricated readiness
 * claim) until it exists.
 */
export class ApiMeridianSource implements MeridianSource {
  async getMeridianIntegration(workspaceId: string) {
    const result = await callPreM3Api<MeridianIntegrationResponse>(
      `v1/workspaces/${encodeURIComponent(workspaceId)}/meridian-integration`,
    );
    return mapPreM3ApiResult(result, toMeridianIntegrationSummary);
  }
}

export const meridianSource: MeridianSource = new ApiMeridianSource();
