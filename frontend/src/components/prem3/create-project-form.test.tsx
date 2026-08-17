import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CreateProjectForm } from "./create-project-form";

const mockCreateProjectAction = vi.fn();
vi.mock("@/app/app/actions", () => ({
  createProjectAction: (...args: unknown[]) => mockCreateProjectAction(...args),
}));

describe("CreateProjectForm", () => {
  it("renders a name-only field -- no technical dataset fields at project creation", () => {
    render(<CreateProjectForm />);

    expect(screen.getByPlaceholderText(/Q3 brand campaign/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/dataset|kpi|grain/i)).not.toBeInTheDocument();
  });

  it("maps a PROJECT_LIMIT_REACHED error to an upgrade CTA, not a generic error message", async () => {
    mockCreateProjectAction.mockResolvedValue({
      errorCode: "PROJECT_LIMIT_REACHED",
      errorMessage: "You have reached your plan's project limit.",
    });
    const user = userEvent.setup();
    render(<CreateProjectForm />);

    await user.type(screen.getByPlaceholderText(/Q3 brand campaign/), "New project");
    await user.click(screen.getByRole("button", { name: "Create MMM Project" }));

    expect(await screen.findByRole("link", { name: "Upgrade" })).toHaveAttribute("href", "/pricing");
  });

  it("renders the server's own error message for any other typed error", async () => {
    mockCreateProjectAction.mockResolvedValue({
      errorCode: "PREM3_API_NOT_CONFIGURED",
      errorMessage: "Project creation isn't connected yet.",
    });
    const user = userEvent.setup();
    render(<CreateProjectForm />);

    await user.type(screen.getByPlaceholderText(/Q3 brand campaign/), "New project");
    await user.click(screen.getByRole("button", { name: "Create MMM Project" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Project creation isn't connected yet.");
  });
});
