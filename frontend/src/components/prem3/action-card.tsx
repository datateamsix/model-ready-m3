import type { ResponseAction } from "@/types/response";

export function ActionCard({ action }: { action: ResponseAction }) {
  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <p className="text-sm font-medium text-prem3-navy">{action.action}</p>
      <p className="mt-1 text-sm text-muted-foreground">{action.reason}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-prem3-navy/70">
        <span className="rounded border border-prem3-cool-gray px-2 py-0.5 font-medium">
          {action.owner}
        </span>
        <span className="rounded border border-prem3-cool-gray px-2 py-0.5">
          {action.can_prem3_execute ? "PreM3 can execute" : "Modeler action"}
        </span>
        {action.requires_approval && (
          <span className="rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-amber-800">
            Requires approval
          </span>
        )}
      </div>
    </div>
  );
}
