import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./status-badge";

describe("StatusBadge", () => {
  it("renders the real status label as text, not only as color", () => {
    render(<StatusBadge status="REVIEW_RECOMMENDED" />);
    expect(screen.getByText("Review recommended")).toBeInTheDocument();
  });

  it("renders BLOCKED distinctly from READY", () => {
    const { rerender } = render(<StatusBadge status="READY" />);
    expect(screen.getByText("Ready")).toBeInTheDocument();
    rerender(<StatusBadge status="BLOCKED" />);
    expect(screen.getByText("Blocked")).toBeInTheDocument();
  });
});
