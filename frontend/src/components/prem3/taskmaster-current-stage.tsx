import { CircleCheck, CircleDashed } from "lucide-react";
import { StatusBadge } from "./status-badge";
import { ProofDrawer } from "./proof-drawer";
import { ResponsePanel } from "./response-panel";
import { deriveArtifactRefs } from "@/lib/format/proof";
import type { TaskmasterStage } from "@/types/ui/taskmaster";
import type { ResponsibleActor } from "@/types/intelligence";

/**
 * M2-13: the operations-workbench detail view for one Taskmaster stage.
 * Every field here (objective/known/missing/owner/currentTask/status) is
 * read straight off the backend stage -- nothing is computed. When the
 * backend supplies a full `detail` response, it's rendered with the
 * existing ResponsePanel/ProofDrawer rather than a parallel presentation,
 * per M2-13's "reuse Mission 1" instruction.
 */
const OWNER_LABEL: Record<ResponsibleActor, string> = {
  PREM3: "PreM3 (autonomous)",
  MARKETER: "Marketer",
  ANALYST: "Analyst",
  DATA_ENGINEER: "Data engineer",
  MODELER: "Modeler",
  SYSTEM_ADMIN: "System admin",
};

export function TaskmasterCurrentStage({ stage }: { stage: TaskmasterStage }) {
  const artifacts = stage.detail ? deriveArtifactRefs(stage.detail) : [];

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-prem3-cool-gray bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
            {stage.label}
          </h2>
          <p className="mt-1 text-sm text-prem3-navy/80">{stage.objective}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={stage.status} />
          {stage.detail && <ProofDrawer artifacts={artifacts} />}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        <span>
          Owner: <span className="font-medium text-prem3-navy">{OWNER_LABEL[stage.owner]}</span>
        </span>
        {stage.requiresApproval && (
          <span className="rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">
            Approval required
          </span>
        )}
      </div>

      {stage.currentTask && (
        <p className="rounded-md bg-prem3-light-gray px-3 py-2 text-sm font-medium text-prem3-navy">
          Current task: {stage.currentTask}
        </p>
      )}

      {(stage.known.length > 0 || stage.missing.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {stage.known.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-prem3-navy/70">Known</p>
              <ul className="flex flex-col gap-1">
                {stage.known.map((item) => (
                  <li key={item} className="flex items-start gap-1.5 text-sm text-prem3-navy/80">
                    <CircleCheck className="mt-0.5 size-3.5 shrink-0 text-emerald-700" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {stage.missing.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-prem3-navy/70">Missing</p>
              <ul className="flex flex-col gap-1">
                {stage.missing.map((item) => (
                  <li key={item} className="flex items-start gap-1.5 text-sm text-prem3-navy/80">
                    <CircleDashed className="mt-0.5 size-3.5 shrink-0 text-prem3-navy/40" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {stage.detail && <ResponsePanel response={stage.detail} />}
    </div>
  );
}
