import type { CreateProjectResult, ProjectSource } from "./project-source";
import type { ProjectDetail, ProjectSummary } from "@/types/ui/commercial";
import { callPreM3Api, mapPreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * Mirrors prem3-api's WorkspaceResponse/WorkspaceListResponse
 * (contracts/openapi.yaml, frozen backend contract commit
 * `e045b4294e2bba36efa74b132e976e0959e2644b`) -- the real wire shape.
 * `workspace_id`/`name`/`status`/`created_at`/`updated_at` only; there is
 * no `dataset_count` or activity field on the backend yet, so the mapping
 * below defaults those honestly (never a fabricated count) rather than
 * inventing them the way the pre-contract version of this file did.
 */
interface WorkspaceResponse {
  workspace_id: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface WorkspaceListResponse {
  items: WorkspaceResponse[];
  next_cursor: string | null;
}

function toProjectStatus(status: string): ProjectSummary["status"] {
  return status.toUpperCase() === "ARCHIVED" ? "ARCHIVED" : "ACTIVE";
}

function toProjectSummary(workspace: WorkspaceResponse): ProjectSummary {
  return {
    workspaceId: workspace.workspace_id,
    name: workspace.name,
    status: toProjectStatus(workspace.status),
    datasetCount: 0,
    latestActivityLabel: null,
  };
}

function toProjectDetail(workspace: WorkspaceResponse): ProjectDetail {
  return {
    workspaceId: workspace.workspace_id,
    name: workspace.name,
    status: toProjectStatus(workspace.status),
    datasetCount: 0,
    planningArtifactCount: null,
    latestEvaluationState: null,
    meridianIntegrationStatus: null,
  };
}

/**
 * The real implementation of ProjectSource -- calls prem3-api's real
 * `/v1/workspaces` endpoints (REQ-016, docs/contracts/BACKEND_REQUESTS.md).
 * Fails loudly with a typed error (never a fabricated project list or a
 * client-simulated creation) until Clerk verification lands (backend
 * Mission 07) -- every authenticated call returns `AUTH_PROVIDER_NOT_
 * CONFIGURED` today even against a running backend.
 */
export class ApiProjectSource implements ProjectSource {
  async listProjects() {
    const result = await callPreM3Api<WorkspaceListResponse>("v1/workspaces");
    return mapPreM3ApiResult(result, (data) => data.items.map(toProjectSummary));
  }

  async createProject(name: string) {
    const result = await callPreM3Api<WorkspaceResponse>("v1/workspaces", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    return mapPreM3ApiResult<WorkspaceResponse, CreateProjectResult>(result, (workspace) => ({
      workspaceId: workspace.workspace_id,
    }));
  }

  async getProject(workspaceId: string) {
    const result = await callPreM3Api<WorkspaceResponse>(`v1/workspaces/${encodeURIComponent(workspaceId)}`);
    return mapPreM3ApiResult(result, toProjectDetail);
  }
}

export const projectSource: ProjectSource = new ApiProjectSource();
