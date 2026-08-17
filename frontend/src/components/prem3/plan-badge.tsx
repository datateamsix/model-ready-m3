import { Sparkle } from "lucide-react";
import type { PlanSummary } from "@/types/ui/commercial";

export function PlanBadge({ plan }: { plan: PlanSummary }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-prem3-cool-gray bg-white px-2.5 py-1 text-xs font-medium text-prem3-navy">
      <Sparkle className="size-3.5 text-prem3-indigo" aria-hidden="true" />
      {plan.displayName}
    </span>
  );
}
