import type { ArtifactRef } from "@/lib/format/proof";
import type { ExperienceBundle } from "@/types/mel";
import type { DomainView } from "@/types/domain-view";
import type { StructuredResponse } from "@/types/response";
import type { RunSummary } from "@/types/run";

/**
 * The StructuredResponse payloads a single run workspace renders, keyed by
 * the section they belong to. Any entry may be null if that response type
 * was never produced for the run (e.g. a run with no scope scenario).
 */
export interface RunResponseSet {
  assessment: StructuredResponse | null;
  feasibility: StructuredResponse | null;
  semanticInterview: StructuredResponse | null;
  scopeScenario: StructuredResponse | null;
  guidedRemediation: StructuredResponse | null;
  officialMeridian: StructuredResponse | null;
  modelReady: StructuredResponse | null;
  learning: StructuredResponse | null;
  domainView: StructuredResponse | null;
}

/**
 * The only data boundary UI components and pages are allowed to depend on.
 * A component that needs run data takes a prop; a page resolves that prop
 * through this interface. Never imported directly by a component — see
 * CLAUDE.md's "components take props, only pages/adapters import fixtures" rule (Task 27).
 */
export interface PreM3DataSource {
  listRuns(): Promise<RunSummary[]>;
  getRun(runId: string): Promise<RunSummary | null>;
  getRunResponses(runId: string): Promise<RunResponseSet>;
  getArtifacts(runId: string): Promise<ArtifactRef[]>;
  getExperience(runId: string): Promise<ExperienceBundle | null>;
  getDomainView(): Promise<DomainView>;
}
