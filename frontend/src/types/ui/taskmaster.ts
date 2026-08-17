/**
 * Frontend-only presentation model for M2-13's Taskmaster read model -- see
 * docs/contracts/BACKEND_REQUESTS.md's REQ-007 M2-13 addition for the exact
 * assumed backend shape this mirrors. Composed entirely from existing
 * hand-mirrored contract types (StructuredResponse, ModelReadyGateEvidence,
 * PresentationStatus, ResponsibleActor) rather than a parallel vocabulary,
 * so Mission 1's ResponsePanel/ModelReadyCard/ProofDrawer can render a
 * stage's detail unchanged once the backend is real.
 *
 * The frontend never computes `status`, `known`, `missing`, or
 * `current_task` -- every field here is read straight from the backend
 * response. There is deliberately no RunStage-derived stage list here (see
 * @/lib/format/timeline, which Mission 1's RunTimeline uses) -- Taskmaster
 * state reconstructs entirely from this read model.
 */
import type { ModelReadyGateEvidence, PresentationStatus, StructuredResponse } from "@/types/response";
import type { ResponsibleActor } from "@/types/intelligence";

export interface TaskmasterStage {
  stageId: string;
  label: string;
  status: PresentationStatus;
  objective: string;
  known: string[];
  missing: string[];
  owner: ResponsibleActor;
  requiresApproval: boolean;
  currentTask: string | null;
  /** Optional full response for this stage; render via the existing
   * ResponsePanel rather than deriving a parallel presentation. */
  detail: StructuredResponse | null;
}

export interface TaskmasterModelReady {
  title: string;
  summary: string;
  status: PresentationStatus;
  gate: ModelReadyGateEvidence;
}

export interface TaskmasterReadModel {
  workspaceId: string;
  datasetId: string | null;
  runId: string | null;
  currentStageId: string | null;
  stages: TaskmasterStage[];
  /** null until the backend's gate evidence says otherwise -- never
   * inferred from stage completion counts. */
  modelReady: TaskmasterModelReady | null;
}
