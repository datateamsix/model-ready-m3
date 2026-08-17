import type { DomainView } from "@/types/domain-view";

export function DomainViewCard({ domainView }: { domainView: DomainView }) {
  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-prem3-navy">DOMAIN_VIEW {domainView.domain_view_version}</p>
        <span className="rounded border border-prem3-cool-gray px-2 py-0.5 text-xs text-prem3-navy/70">
          {domainView.status}
        </span>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs text-prem3-navy/70 sm:grid-cols-4">
        <div>
          <dt className="uppercase tracking-wide">Active claims</dt>
          <dd className="mt-0.5 text-sm font-medium text-prem3-navy">{domainView.claims.length}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Promoted lessons</dt>
          <dd className="mt-0.5 text-sm font-medium text-prem3-navy">{domainView.promoted_lesson_count}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Lesson set version</dt>
          <dd className="mt-0.5 text-sm font-medium text-prem3-navy">{domainView.promoted_lesson_set_version}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Generated</dt>
          <dd className="mt-0.5 text-sm font-medium text-prem3-navy">{domainView.generated_at.slice(0, 10)}</dd>
        </div>
      </dl>

      {domainView.promoted_lesson_count === 0 && (
        <div className="mt-4 rounded-md border border-prem3-cool-gray bg-prem3-light-gray p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-prem3-navy">
            NO EXPERIENTIAL LESSONS PROMOTED
          </p>
          <p className="mt-1 text-sm text-prem3-navy/80">
            PreM3 has captured and reflected on completed assignments, but no candidate has yet
            passed the promotion bar.
          </p>
        </div>
      )}
    </div>
  );
}
