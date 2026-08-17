import { StatusBadge } from "./status-badge";
import type { ResponseFinding } from "@/types/response";

export function FindingCard({ finding }: { finding: ResponseFinding }) {
  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-sm font-semibold text-prem3-navy">{finding.title}</h4>
        <StatusBadge status={finding.disposition} />
      </div>

      <section className="mt-3">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Observed</p>
        <p className="mt-1 text-sm text-prem3-navy">{finding.observed_fact}</p>
      </section>

      {finding.interpretation && (
        <section className="mt-3 rounded-md bg-prem3-light-gray p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-prem3-indigo">Interpretation</p>
          <p className="mt-1 text-sm text-prem3-navy">{finding.interpretation}</p>
        </section>
      )}

      <p className="mt-3 text-sm text-muted-foreground">{finding.why_it_matters}</p>

      <div className="mt-3 flex flex-wrap gap-2">
        <span className="rounded border border-prem3-cool-gray px-2 py-0.5 text-xs text-prem3-navy/70">
          {finding.knowledge_authority_label}
        </span>
        <span className="rounded border border-prem3-cool-gray px-2 py-0.5 text-xs text-prem3-navy/70">
          {finding.decision_authority_label}
        </span>
      </div>
    </div>
  );
}
