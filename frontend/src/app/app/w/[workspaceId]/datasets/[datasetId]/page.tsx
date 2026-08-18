import { AlertTriangle, Database, FlaskConical, Link2, Package, Upload } from "lucide-react";
import { EmptyState } from "@/components/prem3/empty-state";
import { EvaluationHistoryRow } from "@/components/prem3/evaluation-history-row";
import { PageHeader } from "@/components/prem3/page-header";
import { UnlimitedEvaluationsNote } from "@/components/prem3/unlimited-evaluations-note";
import { datasetSource } from "@/lib/adapters/api-dataset-source";
import { routes } from "@/lib/routes";

/**
 * M2-12's Dataset detail page. Identity fields (name/status/timestamps)
 * come from the real, contract-backed DatasetDetail (REQ-011, deployed
 * behind a not-yet-configured auth provider today). The remaining sections
 * -- source inventory, upload/connect state, latest evaluation summary,
 * evaluation history, artifacts, and "Run another evaluation" -- have no
 * backend field or endpoint yet (REQ-014, still NOT STARTED), so each
 * renders its own honest "not yet available" note rather than a fabricated
 * value. Upload is intentionally not built here at all: per REQ-014, the
 * frontend must only ever use backend-issued signed upload URLs, never
 * construct a gs:// URI or hold a credential -- there is nothing safe to
 * build until that contract exists.
 */
const ERROR_MESSAGES: Record<string, string> = {
  PREM3_API_TIMEOUT: "This dataset didn't respond in time. Try again in a moment.",
  PREM3_API_UNREACHABLE: "Couldn't reach this dataset right now. Try again in a moment.",
  UNAUTHENTICATED: "Your session expired. Sign in again.",
};

export default async function Page({
  params,
}: {
  params: Promise<{ workspaceId: string; datasetId: string }>;
}) {
  const { workspaceId, datasetId } = await params;
  const result = await datasetSource.getDataset(workspaceId, datasetId);

  if (!result.ok) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader
          title="Dataset"
          backHref={routes.workspaceDatasets(workspaceId)}
          backLabel="Back to datasets"
        />
        {result.status === 503 ? (
          <EmptyState
            icon={Database}
            title="This dataset isn't connected yet"
            description="prem3-api doesn't have a Dataset detail endpoint deployed yet (docs/contracts/BACKEND_REQUESTS.md REQ-011). This page is wired and ready for when it does."
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

  const dataset = result.data;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title={dataset.name}
        subtitle={`${dataset.status} · Created ${dataset.createdAtLabel} · Updated ${dataset.updatedAtLabel}`}
        backHref={routes.workspaceDatasets(workspaceId)}
        backLabel="Back to datasets"
      />

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <Link2 className="size-4 text-prem3-indigo" aria-hidden="true" />
          Source inventory
        </h2>
        {dataset.sourceCount != null ? (
          <p className="text-sm text-prem3-navy">
            {dataset.sourceCount} source{dataset.sourceCount === 1 ? "" : "s"}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">
            {"Not yet available -- prem3-api doesn't return source inventory yet (REQ-014)."}
          </p>
        )}
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <Upload className="size-4 text-prem3-indigo" aria-hidden="true" />
          Upload / connect state
        </h2>
        <p className="text-sm text-muted-foreground">
          {dataset.uploadState ??
            "Upload isn't wired up yet -- it will only ever use a backend-issued signed upload URL, never a client-held credential (REQ-014)."}
        </p>
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <FlaskConical className="size-4 text-prem3-indigo" aria-hidden="true" />
          Latest evaluation
        </h2>
        {dataset.latestEvaluationStatus ? (
          <p className="text-sm text-prem3-navy">
            {dataset.latestEvaluationStatus} · {dataset.latestEvaluatedAtLabel}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">No evaluation on record yet.</p>
        )}
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-medium text-prem3-navy">
            <FlaskConical className="size-4 text-prem3-indigo" aria-hidden="true" />
            Evaluation history
          </h2>
          <UnlimitedEvaluationsNote />
        </div>
        {dataset.evaluationHistory.length === 0 ? (
          <EmptyState
            icon={FlaskConical}
            title="No evaluations yet"
            description="Evaluation runs will appear here as history for this Dataset once REQ-014's run endpoints exist."
          />
        ) : (
          <ul className="flex flex-col">
            {dataset.evaluationHistory.map((evaluation) => (
              <li key={evaluation.runId}>
                <EvaluationHistoryRow evaluation={evaluation} workspaceId={workspaceId} datasetId={datasetId} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <Package className="size-4 text-prem3-indigo" aria-hidden="true" />
          Artifacts
        </h2>
        <p className="text-sm text-muted-foreground">
          {dataset.artifactCount != null
            ? `${dataset.artifactCount} artifact${dataset.artifactCount === 1 ? "" : "s"}`
            : "Not yet available -- prem3-api doesn't return artifacts yet (REQ-014)."}
        </p>
      </section>

      <button
        type="button"
        disabled
        title="Run another evaluation isn't available yet -- REQ-014's run-creation endpoint doesn't exist."
        className="self-start rounded-md border border-prem3-cool-gray bg-prem3-light-gray px-4 py-2 text-sm font-medium text-prem3-navy/40"
      >
        Run another evaluation
      </button>
    </div>
  );
}
