import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";

describe("/pricing", () => {
  it("makes the 1/10/50 active-project structure unmistakable across the four plans", async () => {
    render(await Page());
    expect(screen.getByText("0 active MMM Projects")).toBeInTheDocument();
    expect(screen.getByText("1 active MMM Project")).toBeInTheDocument();
    expect(screen.getByText("10 active MMM Projects")).toBeInTheDocument();
    expect(screen.getByText("50 active MMM Projects")).toBeInTheDocument();
  });

  it("never presents Dataset as the billing unit -- Dataset is explicitly described as not counted", async () => {
    render(await Page());
    expect(screen.getByText(/never billed or counted/i)).toBeInTheDocument();
  });

  it("clearly explains unlimited re-evaluations as a real product promise", async () => {
    render(await Page());
    expect(screen.getAllByText(/unlimited/i).length).toBeGreaterThan(0);
  });

  it("does not invent a dollar amount anywhere on the page", async () => {
    render(await Page());
    expect(screen.queryByText(/\$\d/)).not.toBeInTheDocument();
  });

  it("does not invent enterprise-only promises like SSO, SLAs, or procurement", async () => {
    render(await Page());
    expect(screen.queryByText(/sso|sla|procurement/i)).not.toBeInTheDocument();
  });

  it("links back to the free Planner", async () => {
    render(await Page());
    expect(screen.getAllByRole("link", { name: /plan my mmm/i })[0]).toHaveAttribute("href", "/planner");
  });
});
