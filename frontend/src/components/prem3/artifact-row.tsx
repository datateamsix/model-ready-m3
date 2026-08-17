import type { ArtifactRef } from "@/lib/format/proof";

export function ArtifactRow({ artifact }: { artifact: ArtifactRef }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-prem3-cool-gray py-2.5 last:border-b-0">
      <div className="flex flex-col">
        <span className="text-sm text-prem3-navy">{artifact.label}</span>
        {artifact.artifact && <span className="text-xs text-muted-foreground">{artifact.artifact}</span>}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-prem3-navy">{artifact.value}</span>
        <span className="rounded border border-prem3-cool-gray px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-prem3-navy/50">
          {artifact.origin}
        </span>
      </div>
    </div>
  );
}
