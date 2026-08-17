import { History } from "lucide-react";
import type { ExperienceApplication } from "@/types/mel";

export function ExperienceAppliedCard({ application }: { application: ExperienceApplication }) {
  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <div className="flex items-center gap-2">
        <History className="size-4 text-prem3-indigo" aria-hidden="true" />
        <p className="text-sm font-semibold text-prem3-navy">Experience applied</p>
      </div>
      <p className="mt-2 text-sm text-prem3-navy">{application.expected_behavior_change}</p>
      {application.observed_behavior_change && (
        <p className="mt-1 text-sm text-muted-foreground">
          Observed: {application.observed_behavior_change}
        </p>
      )}
      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs text-prem3-navy/70">
        <div>
          <dt className="uppercase tracking-wide">Lesson</dt>
          <dd className="mt-0.5 text-prem3-navy">{application.lesson_id}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Retrieved</dt>
          <dd className="mt-0.5 text-prem3-navy">{application.retrieved ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Validation</dt>
          <dd className="mt-0.5 text-prem3-navy">{application.validation_result}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Regression</dt>
          <dd className="mt-0.5 text-prem3-navy">{application.regression_result}</dd>
        </div>
      </dl>
    </div>
  );
}
