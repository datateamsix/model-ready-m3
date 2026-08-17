"use server";

import { redirect } from "next/navigation";
import { projectSource } from "@/lib/adapters/api-project-source";
import { routes } from "@/lib/routes";

/**
 * M2-09's "create/select an MMM Project" entry point for entitled users.
 * Calls the real ProjectSource (which fails loudly, typed, until REQ-011
 * exists -- see docs/contracts/BACKEND_REQUESTS.md) and only ever routes
 * into a next step on a genuine backend-created project. Never simulates a
 * created project by changing client state, and is never called just by
 * `/start` rendering -- only by an explicit form submit.
 */

export type StartStage = "getting-organized" | "ready-to-assess";

export interface CreateProjectActionState {
  errorCode?: string;
  errorMessage?: string;
}

function nextRouteForStage(stage: StartStage, workspaceId: string): string {
  return stage === "ready-to-assess" ? routes.workspaceDatasets(workspaceId) : routes.workspacePlans(workspaceId);
}

export async function createProjectAction(
  _prevState: CreateProjectActionState,
  formData: FormData,
): Promise<CreateProjectActionState> {
  const name = formData.get("name");
  const stage = formData.get("stage");

  if (typeof name !== "string" || name.trim().length === 0) {
    return { errorCode: "INVALID_NAME", errorMessage: "Name your MMM Project to continue." };
  }
  if (stage !== "getting-organized" && stage !== "ready-to-assess") {
    return { errorCode: "INVALID_STAGE", errorMessage: "Something went wrong. Try again." };
  }

  const result = await projectSource.createProject(name.trim());
  if (!result.ok) {
    return { errorCode: result.error.code, errorMessage: result.error.message };
  }

  redirect(nextRouteForStage(stage, result.data.workspaceId));
}
