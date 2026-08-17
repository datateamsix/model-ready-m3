import { FileSearch } from "lucide-react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SectionHeader } from "./section-header";

describe("SectionHeader", () => {
  it("renders the section title and an optional count", () => {
    render(<SectionHeader icon={FileSearch} title="Findings" count={5} />);
    expect(screen.getByRole("heading", { name: /findings/i })).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });
});
