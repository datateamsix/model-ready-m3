import type { ProjectSummary } from "@/types/ui/commercial";
import type { PreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * The only data boundary M2-09's `/start` chooser (and any future project
 * list/create surface) is allowed to depend on -- mirrors BillingSource's
 * pattern (src/lib/adapters/billing-source.ts). Every method returns
 * prem3-api-client.ts's typed Result rather than throwing, so callers render
 * a real blocked/error state instead of an unhandled exception or a
 * fabricated project list.
 */
export interface ProjectsSource {
  listProjects(): Promise<PreM3ApiResult<ProjectSummary[]>>;
  createProject(name: string): Promise<PreM3ApiResult<ProjectSummary>>;
}
