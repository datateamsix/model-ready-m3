import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ActionCard } from "./action-card";
import type { ResponseAction } from "@/types/response";

const action: ResponseAction = {
  action_id: "handoff",
  action: "Proceed to modeler-owned specification and fitting.",
  owner: "MODELER",
  reason: "Posterior sampling remains outside autonomous PreM3 authority.",
  knowledge_class: "MERIDIAN_NORMATIVE",
  decision_class: "MODELER_REVIEW_REQUIRED",
  can_prem3_execute: false,
  requires_approval: false,
  retry_condition: null,
  related_finding_ids: [],
};

describe("ActionCard", () => {
  it("renders the action, its owner, and whether PreM3 can execute it itself", () => {
    render(<ActionCard action={action} />);
    expect(screen.getByText(action.action)).toBeInTheDocument();
    expect(screen.getByText("MODELER")).toBeInTheDocument();
    expect(screen.getByText(/modeler action/i)).toBeInTheDocument();
  });
});
