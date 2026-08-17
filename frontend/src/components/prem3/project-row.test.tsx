import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProjectRow } from "./project-row";
import type { ProjectSummary } from "@/types/ui/commercial";

const project: ProjectSummary = {
  workspaceId: "ws_internal_id_not_shown",
  name: "Acme Media Mix",
  status: "ACTIVE",
  datasetCount: 3,
  latestActivityLabel: "Updated 2 days ago",
};

describe("ProjectRow", () => {
  it("renders the project's customer-facing name and dataset count, never the internal workspaceId", () => {
    render(<ProjectRow project={project} />);
    expect(screen.getByText("Acme Media Mix")).toBeInTheDocument();
    expect(screen.getByText("3 datasets")).toBeInTheDocument();
    expect(screen.queryByText(/ws_internal_id_not_shown/)).not.toBeInTheDocument();
  });

  it("marks an archived project distinctly, not just as another active row", () => {
    render(<ProjectRow project={{ ...project, status: "ARCHIVED" }} />);
    expect(screen.getByText("Archived")).toBeInTheDocument();
  });
});
