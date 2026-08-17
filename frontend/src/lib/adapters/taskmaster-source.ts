import type { TaskmasterReadModel } from "@/types/ui/taskmaster";
import type { PreM3ApiResult } from "@/lib/server/prem3-api-client";

/**
 * The only data boundary M2-13's Taskmaster workspace is allowed to depend
 * on -- mirrors BillingSource/ProjectsSource's pattern. Returns
 * prem3-api-client.ts's typed Result rather than throwing, so the page
 * renders a real blocked state instead of an unhandled exception or a
 * fabricated read model.
 */
export interface TaskmasterSource {
  getTaskmaster(workspaceId: string): Promise<PreM3ApiResult<TaskmasterReadModel>>;
}
