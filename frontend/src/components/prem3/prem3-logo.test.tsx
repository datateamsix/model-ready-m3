import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PreM3Logo } from "./prem3-logo";

describe("PreM3Logo", () => {
  it("renders the approved brand mark with accessible alt text", () => {
    render(<PreM3Logo />);
    expect(screen.getByRole("img", { name: /prem3/i })).toBeInTheDocument();
  });

  it("renders the Map. Mend. Model. tagline when the wordmark is shown", () => {
    render(<PreM3Logo showWordmark />);
    expect(screen.getByText(/map\. mend\. model\./i)).toBeInTheDocument();
  });
});
