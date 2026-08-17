import type { ResponseInsight } from "@/types/response";

export function InsightCard({ insight }: { insight: ResponseInsight }) {
  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <p className="text-sm font-medium text-prem3-navy">{insight.statement}</p>
      <p className="mt-1 text-sm text-muted-foreground">{insight.implication}</p>
      {insight.do_not_claim && (
        <p className="mt-2 text-xs text-amber-800">
          <span className="font-semibold uppercase tracking-wide">Do not claim: </span>
          {insight.do_not_claim}
        </p>
      )}
    </div>
  );
}
