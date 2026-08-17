import { describe, expect, it } from "vitest";
import { modelReadyResponse } from "@/lib/fixtures/responses";
import { deriveArtifactRefs } from "./proof";

describe("deriveArtifactRefs", () => {
  it("derives one artifact ref per proof receipt without inventing new ones", () => {
    const refs = deriveArtifactRefs(modelReadyResponse);
    expect(refs).toHaveLength(modelReadyResponse.proof.receipts.length);
    expect(refs[0].label).toBe(modelReadyResponse.proof.receipts[0].label);
  });
});
