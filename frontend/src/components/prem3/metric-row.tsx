import type { ResponseMetric } from "@/types/response";

export function MetricRow({ metrics }: { metrics: ResponseMetric[] }) {
  if (metrics.length === 0) return null;

  return (
    <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {metrics.map((metric) => (
        <div key={metric.metric_id} className="rounded-md border border-prem3-cool-gray bg-white p-3">
          <dt className="text-xs text-muted-foreground">{metric.label}</dt>
          <dd className="mt-1 text-lg font-semibold text-prem3-navy">
            {String(metric.value ?? "—")}
            {metric.unit ? <span className="ml-1 text-sm font-normal text-muted-foreground">{metric.unit}</span> : null}
          </dd>
        </div>
      ))}
    </dl>
  );
}
