import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { UpgradeCta } from "./upgrade-cta";

describe("UpgradeCta", () => {
  it("links to pricing rather than performing a client-side plan change itself", () => {
    render(<UpgradeCta reason="You've reached your active project limit." />);
    expect(screen.getByText("You've reached your active project limit.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /upgrade/i })).toHaveAttribute("href", "/pricing");
  });
});
