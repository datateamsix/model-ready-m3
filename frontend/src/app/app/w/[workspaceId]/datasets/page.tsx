import { AlertTriangle, Database } from "lucide-react";
import { EmptyState } from "@/components/prem3/empty-state";
import { PageHeader } from "@/components/prem3/page-header";
import { DatasetSummaryRow } from "@/components/prem3/dataset-summary-row";
import { datasetSource } from "@/lib/adapters/api-dataset-source";
import { routes } from "@/lib/routes";

/**
 * M2-12's Dataset list. Every field comes from DatasetSummary
 * (REQ-011/REQ-014, not built yet) -- honest 503 gap, same pattern as
 * every other prompt this session. Upload and Dataset detail are
 * intentionally out of scope for this pass (a much larger surface: signed
 * upload URLs, progress/retry/cancel, run history, artifacts) -- this page
 * only needs the list to exist and be real, not fabricated.
 */
const ERROR_MESSAGES: Record<string, string> = {
  PREM3_API_TIMEOUT: "Datasets didn't respond in time. Try again in a moment.",
  PREM3_API_UNREACHABLE: "Couldn't reach Datasets right now. Try again in a moment.",
  UNAUTHENTICATED: "Your session expired. Sign in again.",
};

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  const result = await datasetSource.listDatasets(workspaceId);

  if (!result.ok) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Datasets" backHref={routes.workspace(workspaceId)} backLabel="Back to project" />
        {result.status === 503 ? (
          <EmptyState
            icon={Database}
            title="Datasets aren't connected yet"
            description="prem3-api doesn't have a Dataset endpoint deployed yet (docs/contracts/BACKEND_REQUESTS.md REQ-011, REQ-014). This page is wired and ready for when it does."
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

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Datasets"
        backHref={routes.workspace(workspaceId)}
        backLabel="Back to project"
      />

      {result.data.length === 0 ? (
        <EmptyState
          icon={Database}
          title="No Datasets yet"
          description="Datasets are added once upload is wired to this MMM Project."
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {result.data.map((dataset) => (
            <li key={dataset.datasetId}>
              <DatasetSummaryRow dataset={dataset} workspaceId={workspaceId} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
