import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";

describe("/how-it-works", () => {
  it("covers the Project -> Dataset -> Evaluation lifecycle", () => {
    render(<Page />);
    expect(screen.getByText("MMM Project")).toBeInTheDocument();
    expect(screen.getByText("Dataset")).toBeInTheDocument();
    expect(screen.getByText("Evaluation")).toBeInTheDocument();
  });

  it("covers the full pipeline including Meridian EDA and BigQuery", () => {
    render(<Page />);
    expect(screen.getByText("Meridian EDA")).toBeInTheDocument();
    expect(screen.getByText("BigQuery")).toBeInTheDocument();
    expect(screen.getByText("Meridian Integration")).toBeInTheDocument();
  });

  it("distinguishes what PreM3 decides from what Meridian officially reports", () => {
    render(<Page />);
    expect(screen.getByText("PreM3 decides")).toBeInTheDocument();
    expect(screen.getByText("Meridian officially reports")).toBeInTheDocument();
  });

  it("states that PreM3 does not autonomously fit the model", () => {
    render(<Page />);
    expect(screen.getByText(/posterior sampling and meridian model fitting stay outside/i)).toBeInTheDocument();
  });
});
