import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";

describe("/ marketing placeholder", () => {
  it("links to the working /app console, not the legacy Mission 1 root", () => {
    render(<Page />);
    expect(screen.getByRole("link", { name: /open prem3/i })).toHaveAttribute("href", "/app");
  });

  it("links to pricing", () => {
    render(<Page />);
    expect(screen.getByRole("link", { name: /see pricing/i })).toHaveAttribute("href", "/pricing");
  });
});
