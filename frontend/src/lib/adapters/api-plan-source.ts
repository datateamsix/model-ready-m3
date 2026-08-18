import type { PlanSource } from "./plan-source";
import type { AcquisitionPlanDetail } from "@/types/ui/commercial";
import { callPreM3Api, mapPreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * REQ-010 is still NOT STARTED (no endpoint, no shape, no deployment) --
 * there is nothing real to mirror yet, unlike REQ-011/016 which have a
 * frozen contract but an unconfigured provider. This assumed shape is
 * recorded in docs/contracts/BACKEND_REQUESTS.md's REQ-010 entry (M2-14
 * addition) so nothing here is invented silently: the frontend is wired
 * against this exact assumption and fails loudly with the typed 503
 * PREM3_API_NOT_CONFIGURED pattern until it's real.
 */
interface PlanResponse {
  planning_run_id: string;
  workspace_id: string;
  objective: string;
  recommended_sources: string[];
  provider_export_requirements: string[];
  fields_to_collect: string[];
  history_grain_guidance: string | null;
  controls_confounders: string[];
  known_gaps: string[];
  owner_label: string | null;
  next_actions: string[];
  provenance_label: string;
  plan_version: string;
  generated_at: string;
}

function toAcquisitionPlanDetail(plan: PlanResponse): AcquisitionPlanDetail {
  return {
    planningRunId: plan.planning_run_id,
    workspaceId: plan.workspace_id,
    objective: plan.objective,
    recommendedSources: plan.recommended_sources,
    providerExportRequirements: plan.provider_export_requirements,
    fieldsToCollect: plan.fields_to_collect,
    historyGrainGuidance: plan.history_grain_guidance,
    controlsConfounders: plan.controls_confounders,
    knownGaps: plan.known_gaps,
    ownerLabel: plan.owner_label,
    nextActions: plan.next_actions,
    provenanceLabel: plan.provenance_label,
    planVersion: plan.plan_version,
    generatedAtLabel: plan.generated_at,
  };
}

/**
 * The real implementation of PlanSource -- calls the assumed
 * `GET /v1/workspaces/{workspace_id}/plans/{planning_run_id}` (REQ-010,
 * not started). Fails loudly with a typed error (never a fabricated plan)
 * until it exists.
 */
export class ApiPlanSource implements PlanSource {
  async getPlan(workspaceId: string, planningRunId: string) {
    const result = await callPreM3Api<PlanResponse>(
      `v1/workspaces/${encodeURIComponent(workspaceId)}/plans/${encodeURIComponent(planningRunId)}`,
    );
    return mapPreM3ApiResult(result, toAcquisitionPlanDetail);
  }
}

export const planSource: PlanSource = new ApiPlanSource();
