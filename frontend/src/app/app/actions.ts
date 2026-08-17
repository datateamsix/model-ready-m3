"use server";

import { redirect } from "next/navigation";
import { projectSource } from "@/lib/adapters/api-project-source";
import { routes } from "@/lib/routes";

/**
 * M2-11's Create MMM Project flow. Calls the real ProjectSource (REQ-016,
 * docs/contracts/BACKEND_REQUESTS.md -- not implemented yet, fails loudly
 * typed until it is). Entitlement enforcement is server-side only: this
 * action never decides locally whether the user is allowed another
 * project, it only relays whatever prem3-api returns.
 */

export interface CreateProjectActionState {
  errorCode?: string;
  errorMessage?: string;
}

export async function createProjectAction(
  _prevState: CreateProjectActionState,
  formData: FormData,
): Promise<CreateProjectActionState> {
  const name = formData.get("name");
  if (typeof name !== "string" || name.trim().length === 0) {
    return { errorCode: "INVALID_NAME", errorMessage: "Give your MMM Project a name." };
  }

  const result = await projectSource.createProject(name.trim());
  if (!result.ok) {
    return { errorCode: result.error.code, errorMessage: result.error.message };
  }

  redirect(routes.workspace(result.data.workspaceId));
}
