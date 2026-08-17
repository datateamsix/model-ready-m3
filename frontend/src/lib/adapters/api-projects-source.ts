import type { ProjectsSource } from "./projects-source";
import type { ProjectSummary } from "@/types/ui/commercial";
import { callPreM3Api } from "@/lib/server/prem3-api-client";

/**
 * The real implementation of ProjectsSource -- calls `prem3-api` through the
 * shared server-only client. Every method fails loudly with a typed error
 * (never a fabricated project list or a client-simulated project) until
 * REQ-011 (see docs/contracts/BACKEND_REQUESTS.md's M2-09 addition) exists;
 * see prem3-api-client.ts's documented-gap discipline.
 */
export class ApiProjectsSource implements ProjectsSource {
  async listProjects() {
    return callPreM3Api<ProjectSummary[]>("v1/projects");
  }

  async createProject(name: string) {
    return callPreM3Api<ProjectSummary>("v1/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }
}

export const projectsSource: ProjectsSource = new ApiProjectsSource();
