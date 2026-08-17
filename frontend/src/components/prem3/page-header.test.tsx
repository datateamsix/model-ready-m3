import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageHeader } from "./page-header";

describe("PageHeader", () => {
  it("renders the title and optional eyebrow/subtitle", () => {
    render(<PageHeader eyebrow="Music Center" title="Dataset A" subtitle="Weekly x geo" />);
    expect(screen.getByRole("heading", { name: "Dataset A" })).toBeInTheDocument();
    expect(screen.getByText("Music Center")).toBeInTheDocument();
    expect(screen.getByText("Weekly x geo")).toBeInTheDocument();
  });

  it("renders an actions slot when provided", () => {
    render(<PageHeader title="Runs" actions={<button>New Assessment</button>} />);
    expect(screen.getByRole("button", { name: "New Assessment" })).toBeInTheDocument();
  });
});
