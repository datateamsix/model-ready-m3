import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthorityBadge } from "./authority-badge";
import type { AuthorityPresentation } from "@/types/response";

const authority: AuthorityPresentation = {
  knowledge_class: "MERIDIAN_NORMATIVE",
  decision_class: "AUTO_BLOCK",
  knowledge_label: "Official Meridian requirement",
  decision_label: "Auto Block",
  rule_id: "MR-020",
  source_url: null,
  blocks_model_ready: true,
};

describe("AuthorityBadge", () => {
  it("renders the backend-provided knowledge label verbatim, not a reworded version", () => {
    render(<AuthorityBadge authority={authority} />);
    expect(screen.getByText("Official Meridian requirement")).toBeInTheDocument();
  });

  it("flags when the authority blocks MODEL_READY", () => {
    render(<AuthorityBadge authority={authority} />);
    expect(screen.getByText(/blocks model_ready/i)).toBeInTheDocument();
  });
});
