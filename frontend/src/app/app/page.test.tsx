import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";

describe("/app console entry", () => {
  it("renders the product line and the Music Center demo run as a recent run", async () => {
    render(await Page());
    expect(screen.getByText(/autonomous pre-modeling for google meridian/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /music center/i })).toBeInTheDocument();
  });

  it("links the Music Center run to the public demo path, not the legacy /runs path", async () => {
    render(await Page());
    const link = screen.getByRole("link", { name: /music center/i });
    expect(link).toHaveAttribute("href", "/app/demo/runs/music-center-dataset-a-demo");
  });

  it("does not present Stride & Field or Summit & Pine as live interactive runs", async () => {
    render(await Page());
    expect(screen.queryByRole("link", { name: /stride & field/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /summit & pine/i })).not.toBeInTheDocument();
    // Both demo assignments (Stride & Field, Summit & Pine) render this
    // note, so it's asserted twice rather than with a singular getByText.
    expect(screen.getAllByText(/not yet available in this workspace/i)).toHaveLength(2);
  });
});
