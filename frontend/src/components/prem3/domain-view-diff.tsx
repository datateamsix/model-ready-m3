import type { DomainViewDiff as DomainViewDiffType } from "@/types/domain-view";

export interface DomainViewDiffProps {
  diff: DomainViewDiffType | null;
  fromVersion: string;
  toVersion: string;
}

export function DomainViewDiff({ diff, fromVersion, toVersion }: DomainViewDiffProps) {
  if (!diff) {
    return (
      <div className="rounded-lg border border-dashed border-prem3-cool-gray bg-white p-4 text-sm text-muted-foreground">
        No DOMAIN_VIEW changes yet — still on v{toVersion}.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <p className="text-sm font-semibold text-prem3-navy">
        {fromVersion} → {toVersion}
      </p>
      <div className="mt-2 flex gap-4 text-sm text-prem3-navy/80">
        <span>Added: {diff.added_claim_ids.length}</span>
        <span>Modified: {diff.modified_claim_ids.length}</span>
        <span>Removed: {diff.removed_claim_ids.length}</span>
      </div>
    </div>
  );
}
