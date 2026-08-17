import { Infinity as InfinityIcon } from "lucide-react";

/**
 * States "unlimited re-evaluations" as an explicit product promise
 * (M2-03's acceptance criterion) -- not represented by the mere absence
 * of a quota UI, and never a literal client-side unbounded loop.
 */
export function UnlimitedEvaluationsNote() {
  return (
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <InfinityIcon className="size-3.5 text-prem3-indigo" aria-hidden="true" />
      Unlimited re-evaluations on every paid plan.
    </p>
  );
}
