import type { ResponseOrigin, StructuredResponse } from "@/types/response";

export interface ArtifactRef {
  label: string;
  value: string;
  origin: ResponseOrigin;
  artifact: string | null;
}

/**
 * Reads a response's already-computed proof bundle into a flat list for
 * ProofDrawer. It never adds an artifact the response didn't already list.
 */
export function deriveArtifactRefs(response: StructuredResponse): ArtifactRef[] {
  const fromReceipts: ArtifactRef[] = response.proof.receipts.map((receipt) => ({
    label: receipt.label,
    value: String(receipt.value ?? ""),
    origin: receipt.origin,
    artifact: receipt.artifact,
  }));

  const fromUris: ArtifactRef[] = response.proof.artifact_uris.map((uri) => ({
    label: "Artifact URI",
    value: uri,
    origin: "RUN_EVIDENCE",
    artifact: uri,
  }));

  return [...fromReceipts, ...fromUris];
}
