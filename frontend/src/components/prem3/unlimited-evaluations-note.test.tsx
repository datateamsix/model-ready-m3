import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { UnlimitedEvaluationsNote } from "./unlimited-evaluations-note";

describe("UnlimitedEvaluationsNote", () => {
  it("states unlimited re-evaluations as a product promise, not a counted allowance", () => {
    render(<UnlimitedEvaluationsNote />);
    expect(screen.getByText(/unlimited re-evaluations/i)).toBeInTheDocument();
  });
});
