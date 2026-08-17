import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PreM3Logo } from "./prem3-logo";

describe("PreM3Logo", () => {
  it("renders the approved brand mark with accessible alt text", () => {
    render(<PreM3Logo />);
    expect(screen.getByRole("img", { name: /prem3/i })).toBeInTheDocument();
  });

  it("renders the PreM3 wordmark, with no tagline, when the wordmark is shown", () => {
    render(<PreM3Logo showWordmark />);
    expect(screen.getByText("PreM3")).toBeInTheDocument();
    expect(screen.queryByText(/map\. mend\. model\./i)).not.toBeInTheDocument();
  });

  it("renders no wordmark text at all when showWordmark is false", () => {
    render(<PreM3Logo />);
    expect(screen.queryByText("PreM3")).not.toBeInTheDocument();
  });
});
