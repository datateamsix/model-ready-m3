import type { TaskmasterSource } from "./taskmaster-source";
import type { TaskmasterReadModel } from "@/types/ui/taskmaster";
import { callPreM3Api } from "@/lib/server/prem3-api-client";

/**
 * The real implementation of TaskmasterSource -- calls `prem3-api` through
 * the shared server-only client. Fails loudly with a typed error (never a
 * fabricated stage list or a client-inferred status) until REQ-007 (see
 * docs/contracts/BACKEND_REQUESTS.md's M2-13 addition) exists.
 */
export class ApiTaskmasterSource implements TaskmasterSource {
  async getTaskmaster(workspaceId: string) {
    return callPreM3Api<TaskmasterReadModel>(`v1/projects/${workspaceId}/taskmaster`);
  }
}

export const taskmasterSource: TaskmasterSource = new ApiTaskmasterSource();
