import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusHeader } from "./status-header";

describe("StatusHeader", () => {
  it("renders the response title, summary, and status badge together", () => {
    render(
      <StatusHeader
        title="MODEL_READY"
        summary="The pre-modeling contract has been verified."
        status="READY"
      />,
    );
    expect(screen.getByRole("heading", { name: "MODEL_READY" })).toBeInTheDocument();
    expect(screen.getByText("The pre-modeling contract has been verified.")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });
});
