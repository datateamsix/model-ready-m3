import { AlertTriangle, Compass, Database, ListChecks, Radar, Rows3 } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/prem3/empty-state";
import { projectSource } from "@/lib/adapters/api-project-source";
import { routes } from "@/lib/routes";

/**
 * M2-11's project home. Answers what this MMM Project is, what belongs to
 * it, and the next useful action -- sourced entirely from ProjectDetail
 * (REQ-016, not built yet). The four section cards link to their owning
 * prompts' routes (M2-12 Datasets, M2-10 Planning, M2-13 Taskmaster, M2-14
 * Meridian Integration) rather than duplicating their content here -- each
 * of those prompts owns its own real data-fetching, this page only needs
 * to exist and route correctly.
 */
const ERROR_MESSAGES: Record<string, string> = {
  PREM3_API_TIMEOUT: "This project didn't respond in time. Try again in a moment.",
  PREM3_API_UNREACHABLE: "Couldn't reach this project right now. Try again in a moment.",
  UNAUTHENTICATED: "Your session expired. Sign in again.",
};

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  const result = await projectSource.getProject(workspaceId);

  if (!result.ok) {
    return result.status === 503 ? (
      <EmptyState
        icon={Compass}
        title="MMM Project isn't connected yet"
        description="prem3-api doesn't have a Project detail endpoint deployed yet (docs/contracts/BACKEND_REQUESTS.md REQ-016). This page is wired and ready for when it does."
      />
    ) : (
      <div
        role="alert"
        className="flex items-start gap-3 rounded-md border border-prem3-cool-gray bg-white px-4 py-3 text-sm text-prem3-navy"
      >
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-prem3-navy/60" aria-hidden="true" />
        <p>{ERROR_MESSAGES[result.error.code] ?? result.error.message}</p>
      </div>
    );
  }

  const project = result.data;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold text-prem3-navy">
          {project.name}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {project.status} · {project.datasetCount} dataset{project.datasetCount === 1 ? "" : "s"}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          href={routes.workspaceDatasets(workspaceId)}
          className="flex flex-col gap-1 rounded-lg border border-prem3-cool-gray bg-white p-5 transition-colors hover:border-prem3-indigo"
        >
          <Database className="size-5 text-prem3-indigo" aria-hidden="true" />
          <p className="text-sm font-medium text-prem3-navy">Datasets</p>
          <p className="text-xs text-muted-foreground">{project.datasetCount} dataset{project.datasetCount === 1 ? "" : "s"}</p>
        </Link>

        <Link
          href={routes.workspacePlans(workspaceId)}
          className="flex flex-col gap-1 rounded-lg border border-prem3-cool-gray bg-white p-5 transition-colors hover:border-prem3-indigo"
        >
          <ListChecks className="size-5 text-prem3-indigo" aria-hidden="true" />
          <p className="text-sm font-medium text-prem3-navy">Planning</p>
          <p className="text-xs text-muted-foreground">
            {project.planningArtifactCount != null
              ? `${project.planningArtifactCount} planning artifact${project.planningArtifactCount === 1 ? "" : "s"}`
              : "Not yet available"}
          </p>
        </Link>

        <Link
          href={routes.workspaceTaskmaster(workspaceId)}
          className="flex flex-col gap-1 rounded-lg border border-prem3-cool-gray bg-white p-5 transition-colors hover:border-prem3-indigo"
        >
          <Rows3 className="size-5 text-prem3-indigo" aria-hidden="true" />
          <p className="text-sm font-medium text-prem3-navy">Taskmaster</p>
          <p className="text-xs text-muted-foreground">
            {project.latestEvaluationState ?? "No evaluation yet"}
          </p>
        </Link>

        <Link
          href={routes.workspaceMeridian(workspaceId)}
          className="flex flex-col gap-1 rounded-lg border border-prem3-cool-gray bg-white p-5 transition-colors hover:border-prem3-indigo"
        >
          <Radar className="size-5 text-prem3-indigo" aria-hidden="true" />
          <p className="text-sm font-medium text-prem3-navy">Meridian Integration</p>
          <p className="text-xs text-muted-foreground">{project.meridianIntegrationStatus ?? "Not yet available"}</p>
        </Link>
      </div>
    </div>
  );
}
