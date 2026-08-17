import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DomainViewDiff } from "./domain-view-diff";

describe("DomainViewDiff", () => {
  it("shows an honest no-change state when there is no diff yet", () => {
    render(<DomainViewDiff diff={null} fromVersion="1.0.0" toVersion="1.0.0" />);
    expect(screen.getByText(/no domain_view changes yet/i)).toBeInTheDocument();
    expect(screen.getByText(/still on v1\.0\.0/i)).toBeInTheDocument();
  });

  it("renders added/modified/removed counts when a real diff is given", () => {
    render(
      <DomainViewDiff
        diff={{
          added_claim_ids: ["DV-100"],
          removed_claim_ids: [],
          modified_claim_ids: ["DV-002"],
          authority_changes: [],
          scope_changes: [],
          source_updates: [],
          experiential_learning_changes: ["DV-100"],
          change_types: ["EXPERIENCE_LEARNED"],
        }}
        fromVersion="1.0.0"
        toVersion="1.1.0"
      />,
    );
    expect(screen.getByText("1.0.0 → 1.1.0")).toBeInTheDocument();
    expect(screen.getByText("Added: 1")).toBeInTheDocument();
    expect(screen.getByText("Modified: 1")).toBeInTheDocument();
    expect(screen.getByText("Removed: 0")).toBeInTheDocument();
  });
});
