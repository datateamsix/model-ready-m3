import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProofDrawer } from "./proof-drawer";
import type { ArtifactRef } from "@/lib/format/proof";

const artifacts: ArtifactRef[] = [
  { label: "BigQuery verified", value: "true", origin: "RUN_EVIDENCE", artifact: null },
  { label: "Official ERROR count", value: "0", origin: "OFFICIAL_MERIDIAN", artifact: null },
];

describe("ProofDrawer", () => {
  it("opens on click and lists every artifact it was given", async () => {
    const user = userEvent.setup();
    render(<ProofDrawer artifacts={artifacts} />);

    await user.click(screen.getByRole("button", { name: /view proof/i }));

    expect(await screen.findByText("BigQuery verified")).toBeInTheDocument();
    expect(screen.getByText("Official ERROR count")).toBeInTheDocument();
  });
});
