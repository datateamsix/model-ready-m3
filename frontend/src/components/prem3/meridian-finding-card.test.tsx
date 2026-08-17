import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MeridianFindingCard } from "./meridian-finding-card";
import type { OfficialMeridianView } from "@/types/response";

const finding: OfficialMeridianView = {
  finding_id: "EDA-1",
  severity: "ATTENTION",
  finding_text: "Official collinearity attention.",
  metadata: { check_type: "MULTICOLLINEARITY" },
  prem3_why_it_matters: "Channel effects may be hard to separate.",
  prem3_guidance: null,
  next_action_id: null,
};

describe("MeridianFindingCard", () => {
  it("renders the official finding and PreM3's interpretation as separate labeled sections", () => {
    render(<MeridianFindingCard finding={finding} />);
    const officialSection = screen.getByText(/^official meridian$/i).closest("section");
    const interpretationSection = screen.getByText(/^prem3 interpretation$/i).closest("section");
    expect(officialSection).not.toBe(interpretationSection);
    expect(officialSection).toHaveTextContent(finding.finding_text);
    expect(interpretationSection).toHaveTextContent(finding.prem3_why_it_matters as string);
  });

  it("renders the literal official severity without rewording it", () => {
    render(<MeridianFindingCard finding={finding} />);
    expect(screen.getByText("ATTENTION")).toBeInTheDocument();
  });

  it("does not render a PreM3 interpretation section when none was given", () => {
    render(<MeridianFindingCard finding={{ ...finding, prem3_why_it_matters: null, prem3_guidance: null }} />);
    expect(screen.queryByText(/^prem3 interpretation$/i)).not.toBeInTheDocument();
  });
});
