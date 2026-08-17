import { deriveArtifactRefs } from "@/lib/format/proof";
import { domainViewV1 } from "@/lib/fixtures/domain-view";
import { musicCenterExperienceBundle } from "@/lib/fixtures/experience";
import {
  blockedResponse,
  datasetAAssessmentResponse,
  datasetAFeasibilityResponse,
  datasetAScopeScenarioResponse,
  datasetASemanticInterviewResponse,
  domainViewResponse,
  guidedRemediationResponse,
  learningResponse,
  modelReadyResponse,
  officialMeridianResponse,
} from "@/lib/fixtures/responses";
import { RUN_LIST, RUNS_BY_ID } from "@/lib/fixtures/runs";
import type { ExperienceBundle } from "@/types/mel";
import type { DomainView } from "@/types/domain-view";
import type { RunSummary } from "@/types/run";
import type { ArtifactRef } from "@/lib/format/proof";
import type { PreM3DataSource, RunResponseSet } from "./data-source";

const MUSIC_CENTER_RUN_ID = "music-center-dataset-a-demo";

const MUSIC_CENTER_RESPONSES: RunResponseSet = {
  assessment: datasetAAssessmentResponse,
  feasibility: datasetAFeasibilityResponse,
  semanticInterview: datasetASemanticInterviewResponse,
  scopeScenario: datasetAScopeScenarioResponse,
  guidedRemediation: guidedRemediationResponse,
  officialMeridian: officialMeridianResponse,
  modelReady: modelReadyResponse,
  learning: learningResponse,
  domainView: domainViewResponse,
};

const EMPTY_RESPONSES: RunResponseSet = {
  assessment: null,
  feasibility: null,
  semanticInterview: null,
  scopeScenario: null,
  guidedRemediation: null,
  officialMeridian: null,
  modelReady: blockedResponse,
  learning: null,
  domainView: null,
};

/**
 * Reads from the fixtures under lib/fixtures/. This is the only
 * PreM3DataSource implementation Mission 1 ships — there is no live
 * backend to call yet (see Task 13 / api-data-source.ts).
 */
export class FixturePreM3DataSource implements PreM3DataSource {
  async listRuns(): Promise<RunSummary[]> {
    return RUN_LIST;
  }

  async getRun(runId: string): Promise<RunSummary | null> {
    return RUNS_BY_ID[runId] ?? null;
  }

  async getRunResponses(runId: string): Promise<RunResponseSet> {
    if (runId === MUSIC_CENTER_RUN_ID) return MUSIC_CENTER_RESPONSES;
    return EMPTY_RESPONSES;
  }

  async getArtifacts(runId: string): Promise<ArtifactRef[]> {
    if (runId !== MUSIC_CENTER_RUN_ID) return [];
    return deriveArtifactRefs(modelReadyResponse);
  }

  async getExperience(runId: string): Promise<ExperienceBundle | null> {
    if (runId !== MUSIC_CENTER_RUN_ID) return null;
    return musicCenterExperienceBundle;
  }

  async getDomainView(): Promise<DomainView> {
    return domainViewV1;
  }
}

export const preM3DataSource: PreM3DataSource = new FixturePreM3DataSource();
