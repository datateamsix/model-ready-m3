import { AlertTriangle, BarChart3, CheckCircle2, Cloud, Database, ListChecks, Package, Radar } from "lucide-react";
import { EmptyState } from "@/components/prem3/empty-state";
import { PageHeader } from "@/components/prem3/page-header";
import { StatusBadge } from "@/components/prem3/status-badge";
import { meridianSource } from "@/lib/adapters/api-meridian-source";
import { routes } from "@/lib/routes";

/**
 * M2-14's Meridian Integration surface. User-facing term is always
 * "Meridian Integration" -- this reports what PreM3 has prepared for
 * Meridian (EDA report, model-ready data, BigQuery publish, artifacts,
 * integration checks, readiness receipt), never a claim that PreM3 fit a
 * Meridian model itself. No backend field covers any of this yet (REQ-017,
 * a newly filed gap), so every section renders its own honest "not yet
 * available" note rather than a fabricated readiness signal.
 */
const ERROR_MESSAGES: Record<string, string> = {
  PREM3_API_TIMEOUT: "Meridian Integration didn't respond in time. Try again in a moment.",
  PREM3_API_UNREACHABLE: "Couldn't reach Meridian Integration right now. Try again in a moment.",
  UNAUTHENTICATED: "Your session expired. Sign in again.",
};

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  const result = await meridianSource.getMeridianIntegration(workspaceId);

  if (!result.ok) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader
          title="Meridian Integration"
          backHref={routes.workspace(workspaceId)}
          backLabel="Back to project"
        />
        {result.status === 503 ? (
          <EmptyState
            icon={Radar}
            title="Meridian Integration isn't connected yet"
            description="prem3-api doesn't have a Meridian Integration endpoint deployed yet (docs/contracts/BACKEND_REQUESTS.md REQ-017). This page is wired and ready for when it does."
          />
        ) : (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-md border border-prem3-cool-gray bg-white px-4 py-3 text-sm text-prem3-navy"
          >
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-prem3-navy/60" aria-hidden="true" />
            <p>{ERROR_MESSAGES[result.error.code] ?? result.error.message}</p>
          </div>
        )}
      </div>
    );
  }

  const meridian = result.data;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Meridian Integration"
        subtitle="What PreM3 has prepared for Meridian -- not a claim that PreM3 fit a Meridian model itself."
        backHref={routes.workspace(workspaceId)}
        backLabel="Back to project"
      />

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <BarChart3 className="size-4 text-prem3-indigo" aria-hidden="true" />
          Official Meridian EDA report
        </h2>
        {meridian.edaReportStatus ? (
          <p className="text-sm text-prem3-navy">
            {meridian.edaReportUrl ? (
              <a href={meridian.edaReportUrl} className="underline hover:text-prem3-indigo">
                {meridian.edaReportStatus}
              </a>
            ) : (
              meridian.edaReportStatus
            )}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">Not yet available.</p>
        )}
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <Database className="size-4 text-prem3-indigo" aria-hidden="true" />
          Model-ready data
        </h2>
        <p className="text-sm text-muted-foreground">
          {meridian.modelReadyDataLocationLabel ?? "Not yet available."}
        </p>
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <Cloud className="size-4 text-prem3-indigo" aria-hidden="true" />
          BigQuery publish
        </h2>
        <p className="text-sm text-muted-foreground">
          {meridian.bigQueryPublishVerified == null
            ? "Not yet available."
            : meridian.bigQueryPublishVerified
              ? "Verified."
              : "Not yet verified."}
        </p>
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <Package className="size-4 text-prem3-indigo" aria-hidden="true" />
          Required artifacts
        </h2>
        {meridian.requiredArtifacts.length === 0 ? (
          <p className="text-sm text-muted-foreground">Not yet available.</p>
        ) : (
          <ul className="flex flex-col gap-1 text-sm text-prem3-navy">
            {meridian.requiredArtifacts.map((artifact) => (
              <li key={artifact}>{artifact}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <ListChecks className="size-4 text-prem3-indigo" aria-hidden="true" />
          Integration checks
        </h2>
        {meridian.integrationChecks.length === 0 ? (
          <p className="text-sm text-muted-foreground">Not yet available.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {meridian.integrationChecks.map((check) => (
              <li key={check.label} className="flex items-center justify-between gap-3">
                <span className="text-sm text-prem3-navy">{check.label}</span>
                <StatusBadge status={check.status} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <CheckCircle2 className="size-4 text-prem3-indigo" aria-hidden="true" />
          Readiness receipt
        </h2>
        <p className="text-sm text-muted-foreground">{meridian.readinessReceiptLabel ?? "Not yet available."}</p>
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <Radar className="size-4 text-prem3-indigo" aria-hidden="true" />
          Next approved modeling action
        </h2>
        <p className="text-sm text-muted-foreground">
          {meridian.nextApprovedModelingAction ?? "Not yet available."}
        </p>
      </section>
    </div>
  );
}
