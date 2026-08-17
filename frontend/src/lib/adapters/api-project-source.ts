import type { CreateProjectResult, ProjectSource } from "./project-source";
import type { ProjectDetail, ProjectSummary } from "@/types/ui/commercial";
import { callPreM3Api } from "@/lib/server/prem3-api-client";

/**
 * The real implementation of ProjectSource -- calls `prem3-api` through the
 * shared server-only client, against REQ-016
 * (docs/contracts/BACKEND_REQUESTS.md, filed by M2-11). Fails loudly with a
 * typed error (never a fabricated project list or a client-simulated
 * creation) until that endpoint exists.
 */
export class ApiProjectSource implements ProjectSource {
  async listProjects() {
    return callPreM3Api<ProjectSummary[]>("v1/projects");
  }

  async createProject(name: string) {
    return callPreM3Api<CreateProjectResult>("v1/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }

  async getProject(workspaceId: string) {
    return callPreM3Api<ProjectDetail>(`v1/projects/${encodeURIComponent(workspaceId)}`);
  }
}

export const projectSource: ProjectSource = new ApiProjectSource();
