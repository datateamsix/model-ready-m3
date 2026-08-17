import type { ScenarioView } from "@/types/response";

export function ScenarioCard({ scenario }: { scenario: ScenarioView }) {
  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-prem3-navy">{scenario.title}</p>
        {scenario.read_only && (
          <span className="shrink-0 rounded border border-prem3-cool-gray px-2 py-0.5 text-xs text-prem3-navy/70">
            Read-only simulation
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{scenario.assumption}</p>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
        <div>
          <dt className="font-semibold uppercase tracking-wide text-prem3-navy/70">Improves</dt>
          <dd className="mt-0.5 text-prem3-navy">{scenario.what_improves}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-wide text-prem3-navy/70">Does not change</dt>
          <dd className="mt-0.5 text-prem3-navy">{scenario.what_does_not_change}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-prem3-navy/70">{scenario.required_review}</p>
    </div>
  );
}
