import { AlertTriangle, LayoutGrid } from "lucide-react";
import { EmptyState } from "@/components/prem3/empty-state";
import { PageHeader } from "@/components/prem3/page-header";
import { TaskmasterStageRail } from "@/components/prem3/taskmaster-stage-rail";
import { TaskmasterCurrentStage } from "@/components/prem3/taskmaster-current-stage";
import { ModelReadyCard } from "@/components/prem3/model-ready-card";
import { taskmasterSource } from "@/lib/adapters/api-taskmaster-source";
import { routes } from "@/lib/routes";

/**
 * M2-13: the authenticated Taskmaster execution workbench. Everything
 * rendered here comes straight from taskmasterSource's read model -- no
 * RunStage derivation, no client-computed status/progress. Fails loudly
 * with an honest blocked state (see ERROR_MESSAGES) until REQ-007 exists
 * (docs/contracts/BACKEND_REQUESTS.md).
 */
const ERROR_MESSAGES: Record<string, string> = {
  PREM3_API_TIMEOUT: "Taskmaster didn't respond in time. Try again in a moment.",
  PREM3_API_UNREACHABLE: "Couldn't reach Taskmaster right now. Try again in a moment.",
  UNAUTHENTICATED: "Your session expired. Sign in again to view Taskmaster.",
};

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  const result = await taskmasterSource.getTaskmaster(workspaceId);

  if (!result.ok) {
    return (
      <div className="flex flex-col gap-8">
        <PageHeader
          eyebrow="MMM Project"
          title="Taskmaster"
          subtitle={`Workspace ${workspaceId}`}
          backHref={routes.workspace(workspaceId)}
          backLabel="Back to project"
        />
        {result.status === 503 ? (
          <EmptyState
            icon={LayoutGrid}
            title="Taskmaster isn't connected yet"
            description="prem3-api doesn't have a Taskmaster read-model endpoint deployed yet (docs/contracts/BACKEND_REQUESTS.md REQ-007). This page is wired and ready for when it does."
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

  const { stages, currentStageId, modelReady } = result.data;
  const currentStage = stages.find((stage) => stage.stageId === currentStageId) ?? stages[0] ?? null;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="MMM Project"
        title="Taskmaster"
        subtitle={`Workspace ${workspaceId}`}
        backHref={routes.workspace(workspaceId)}
        backLabel="Back to project"
      />

      {stages.length === 0 ? (
        <EmptyState
          icon={LayoutGrid}
          title="No Taskmaster stages yet"
          description="This Project doesn't have a Taskmaster run in progress."
        />
      ) : (
        <>
          <TaskmasterStageRail stages={stages} currentStageId={currentStageId} />
          {currentStage && <TaskmasterCurrentStage stage={currentStage} />}
        </>
      )}

      {modelReady && (
        <ModelReadyCard
          title={modelReady.title}
          summary={modelReady.summary}
          status={modelReady.status}
          gate={modelReady.gate}
        />
      )}
    </div>
  );
}
