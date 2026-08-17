import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";

describe("/ marketing homepage", () => {
  it("renders the real headline and both primary CTAs, routed correctly", () => {
    render(<Page />);
    expect(
      screen.getByRole("heading", { level: 1, name: /map the data\. mend what's broken\. prove it's model-ready\./i }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /plan my mmm/i })[0]).toHaveAttribute(
      "href",
      "/planner",
    );
    expect(screen.getByRole("link", { name: /see how it works/i })).toHaveAttribute(
      "href",
      "/how-it-works",
    );
  });

  it("renders the real completed Music Center run timeline as hero proof, not an illustration", () => {
    render(<Page />);
    expect(screen.getByTestId("stage-COMPLETE")).toHaveAttribute("data-status", "COMPLETE");
  });

  it("renders the real official Meridian finding, kept separate from PreM3's interpretation", () => {
    render(<Page />);
    expect(screen.getByText("Official collinearity attention.")).toBeInTheDocument();
    expect(screen.getByText("Channel effects may be hard to separate.")).toBeInTheDocument();
  });

  it("does not invent testimonials, customer logos, or usage metrics", () => {
    render(<Page />);
    expect(screen.queryByText(/testimonial|% of users|trusted by/i)).not.toBeInTheDocument();
  });

  it("links to pricing rather than rendering a full pricing grid on the homepage", () => {
    render(<Page />);
    expect(screen.getByRole("link", { name: /see pricing/i })).toHaveAttribute("href", "/pricing");
  });
});
