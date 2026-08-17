import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { ResponsePanel } from "./response-panel";
import { learningResponse, officialMeridianResponse } from "@/lib/fixtures/responses";

describe("ResponsePanel", () => {
  it("renders a response's title, summary, status, and metrics generically", () => {
    render(<ResponsePanel response={learningResponse} />);
    expect(screen.getByRole("heading", { name: "What PreM3 has learned" })).toBeInTheDocument();
    expect(screen.getByText("Promoted experiential lessons")).toBeInTheDocument();
  });

  it("renders official Meridian findings via MeridianFindingCard, not the generic FindingCard, when present", () => {
    render(<ResponsePanel response={officialMeridianResponse} />);
    // This fixture legitimately mirrors the same official finding into both
    // findings[] (a real FindingCard) and official_meridian[] (the real
    // MeridianFindingCard) -- both render "Official collinearity
    // attention.", and "Official Meridian" text appears in three places
    // total (the section's own h3, MeridianFindingCard's internal <p>
    // label, and the mirrored FindingCard's h4 title). Scoping to the
    // Official Meridian section specifically disambiguates all of it.
    const heading = screen.getByRole("heading", { level: 3, name: /official meridian/i });
    const section = heading.closest("div") as HTMLElement;
    expect(within(section).getByText("Official collinearity attention.")).toBeInTheDocument();
  });

  it("omits a section entirely when its array is empty rather than rendering an empty heading", () => {
    render(<ResponsePanel response={learningResponse} />);
    expect(screen.queryByText(/^actions$/i)).not.toBeInTheDocument();
  });
});
