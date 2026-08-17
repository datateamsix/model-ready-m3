import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockCreateProjectAction = vi.fn();
vi.mock("@/app/(marketing)/start/actions", () => ({
  createProjectAction: (...args: unknown[]) => mockCreateProjectAction(...args),
}));

import { CreateProjectForm } from "./create-project-form";

describe("CreateProjectForm", () => {
  it("renders a name field and the given submit label", () => {
    render(<CreateProjectForm stage="getting-organized" label="Create and start planning" />);

    expect(screen.getByLabelText(/new mmm project name/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create and start planning" })).toBeInTheDocument();
  });

  it("submits the stage as a hidden field alongside the name", async () => {
    mockCreateProjectAction.mockResolvedValue({});
    const user = userEvent.setup();
    render(<CreateProjectForm stage="ready-to-assess" label="Create and continue" />);

    await user.type(screen.getByLabelText(/new mmm project name/i), "Acme MMM");
    await user.click(screen.getByRole("button", { name: "Create and continue" }));

    expect(mockCreateProjectAction).toHaveBeenCalled();
    const submittedFormData = mockCreateProjectAction.mock.calls[0][1] as FormData;
    expect(submittedFormData.get("name")).toBe("Acme MMM");
    expect(submittedFormData.get("stage")).toBe("ready-to-assess");
  });

  it("shows the backend's typed error message instead of a fabricated success", async () => {
    mockCreateProjectAction.mockResolvedValue({
      errorCode: "PREM3_API_NOT_CONFIGURED",
      errorMessage: "not configured",
    });
    const user = userEvent.setup();
    render(<CreateProjectForm stage="getting-organized" label="Create" />);

    await user.type(screen.getByLabelText(/new mmm project name/i), "Acme MMM");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("not configured");
  });
});
