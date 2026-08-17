import type { ProjectDetail, ProjectSummary } from "@/types/ui/commercial";
import type { PreM3ApiResult } from "@/lib/server/prem3-api-client";

export interface CreateProjectResult {
  workspaceId: string;
}

/**
 * The only data boundary the dashboard, project-creation flow, and project
 * home are allowed to depend on -- mirrors BillingSource's pattern
 * (src/lib/adapters/billing-source.ts). REQ-016
 * (docs/contracts/BACKEND_REQUESTS.md) specifies the backend contract this
 * implements against; it does not exist yet, so every method fails loudly
 * with a typed error until it does.
 */
export interface ProjectSource {
  listProjects(): Promise<PreM3ApiResult<ProjectSummary[]>>;
  createProject(name: string): Promise<PreM3ApiResult<CreateProjectResult>>;
  getProject(workspaceId: string): Promise<PreM3ApiResult<ProjectDetail>>;
}
