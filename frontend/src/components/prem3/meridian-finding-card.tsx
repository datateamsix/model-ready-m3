import { cn } from "@/lib/utils";
import type { OfficialMeridianView } from "@/types/response";

/*
 * A direct Record keyed by the literal official severity value, deliberately
 * not routed through severityTone/StatusTone (Task 8) — that vocabulary is
 * for PresentationStatus. Keeping this map separate and 1:1 with
 * OfficialMeridianView["severity"] makes it structurally impossible to
 * reword or drop one of ERROR/ATTENTION/INFO.
 */
const SEVERITY_CLASSES: Record<OfficialMeridianView["severity"], string> = {
  ERROR: "bg-red-50 text-red-800 border-red-200",
  ATTENTION: "bg-amber-50 text-amber-800 border-amber-200",
  INFO: "bg-prem3-light-gray text-prem3-navy/70 border-prem3-cool-gray",
};

export function MeridianFindingCard({ finding }: { finding: OfficialMeridianView }) {
  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <section>
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-prem3-navy/70">
            Official Meridian
          </p>
          <span
            className={cn(
              "rounded border px-2 py-0.5 text-xs font-semibold",
              SEVERITY_CLASSES[finding.severity],
            )}
          >
            {finding.severity}
          </span>
        </div>
        <p className="mt-1 text-sm text-prem3-navy">{finding.finding_text}</p>
      </section>

      {(finding.prem3_why_it_matters || finding.prem3_guidance) && (
        <section className="mt-3 rounded-md bg-prem3-light-gray p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-prem3-indigo">
            PreM3 interpretation
          </p>
          {finding.prem3_why_it_matters && (
            <p className="mt-1 text-sm text-prem3-navy">{finding.prem3_why_it_matters}</p>
          )}
          {finding.prem3_guidance && (
            <p className="mt-1 text-sm text-prem3-navy">{finding.prem3_guidance}</p>
          )}
        </section>
      )}
    </div>
  );
}
