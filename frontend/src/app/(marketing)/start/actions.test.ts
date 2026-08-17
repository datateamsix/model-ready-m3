import { afterEach, describe, expect, it, vi } from "vitest";

const mockRedirect = vi.fn();
vi.mock("next/navigation", () => ({
  redirect: (...args: unknown[]) => mockRedirect(...args),
}));

const mockCreateProject = vi.fn();
vi.mock("@/lib/adapters/api-projects-source", () => ({
  projectsSource: { createProject: (...args: unknown[]) => mockCreateProject(...args) },
}));

import { createProjectAction } from "./actions";

function formDataFor(fields: Record<string, string>): FormData {
  const formData = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    formData.set(key, value);
  }
  return formData;
}

describe("createProjectAction", () => {
  afterEach(() => {
    mockRedirect.mockReset();
    mockCreateProject.mockReset();
  });

  it("rejects an empty project name without ever calling the backend", async () => {
    const result = await createProjectAction({}, formDataFor({ name: "  ", stage: "getting-organized" }));

    expect(result.errorCode).toBe("INVALID_NAME");
    expect(mockCreateProject).not.toHaveBeenCalled();
  });

  it("rejects an unrecognized stage without ever calling the backend", async () => {
    const result = await createProjectAction({}, formDataFor({ name: "Acme MMM", stage: "not-a-real-stage" }));

    expect(result.errorCode).toBe("INVALID_STAGE");
    expect(mockCreateProject).not.toHaveBeenCalled();
  });

  it("creates the project with the trimmed name, never a client-invented id", async () => {
    mockCreateProject.mockResolvedValue({
      ok: true,
      data: { workspaceId: "ws_1", name: "Acme MMM", status: "ACTIVE", datasetCount: 0, latestActivityLabel: null },
    });

    await createProjectAction({}, formDataFor({ name: "  Acme MMM  ", stage: "getting-organized" }));

    expect(mockCreateProject).toHaveBeenCalledWith("Acme MMM");
  });

  it("routes a getting-organized creation into the project's planning route", async () => {
    mockCreateProject.mockResolvedValue({
      ok: true,
      data: { workspaceId: "ws_1", name: "Acme MMM", status: "ACTIVE", datasetCount: 0, latestActivityLabel: null },
    });

    await createProjectAction({}, formDataFor({ name: "Acme MMM", stage: "getting-organized" }));

    expect(mockRedirect).toHaveBeenCalledWith("/app/w/ws_1/plans");
  });

  it("routes a ready-to-assess creation into the project's datasets route", async () => {
    mockCreateProject.mockResolvedValue({
      ok: true,
      data: { workspaceId: "ws_2", name: "Acme MMM", status: "ACTIVE", datasetCount: 0, latestActivityLabel: null },
    });

    await createProjectAction({}, formDataFor({ name: "Acme MMM", stage: "ready-to-assess" }));

    expect(mockRedirect).toHaveBeenCalledWith("/app/w/ws_2/datasets");
  });

  it("returns the backend's typed error instead of redirecting or fabricating a project", async () => {
    mockCreateProject.mockResolvedValue({
      ok: false,
      status: 503,
      error: { code: "PREM3_API_NOT_CONFIGURED", message: "not configured", requestId: "r1" },
    });

    const result = await createProjectAction({}, formDataFor({ name: "Acme MMM", stage: "getting-organized" }));

    expect(result).toEqual({ errorCode: "PREM3_API_NOT_CONFIGURED", errorMessage: "not configured" });
    expect(mockRedirect).not.toHaveBeenCalled();
  });
});
