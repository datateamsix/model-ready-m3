import { AlertTriangle, ClipboardList, Route } from "lucide-react";
import { EmptyState } from "@/components/prem3/empty-state";
import { PageHeader } from "@/components/prem3/page-header";
import { planSource } from "@/lib/adapters/api-plan-source";
import { routes } from "@/lib/routes";

/**
 * M2-14's acquisition plan detail page. An actionable artifact, not a chat
 * transcript -- every section below is a direct, contract-backed field
 * (REQ-010), never a re-derived summary. REQ-010 is still NOT STARTED (the
 * same backend surface M2-10's planning intake needs, also out of scope
 * this session -- there is no way to reach this page with a real
 * `planningRunId` yet either), so this fails loudly with the typed 503
 * PREM3_API_NOT_CONFIGURED pattern until it exists. Share-link support
 * (REQ-008) is optional per the prompt and REQ-008 is also NOT STARTED, so
 * it's not built here.
 */
const ERROR_MESSAGES: Record<string, string> = {
  PREM3_API_TIMEOUT: "This plan didn't respond in time. Try again in a moment.",
  PREM3_API_UNREACHABLE: "Couldn't reach this plan right now. Try again in a moment.",
  UNAUTHENTICATED: "Your session expired. Sign in again.",
};

export default async function Page({
  params,
}: {
  params: Promise<{ workspaceId: string; planningRunId: string }>;
}) {
  const { workspaceId, planningRunId } = await params;
  const result = await planSource.getPlan(workspaceId, planningRunId);

  if (!result.ok) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Acquisition plan" backHref={routes.workspacePlans(workspaceId)} backLabel="Back to planning" />
        {result.status === 503 ? (
          <EmptyState
            icon={Route}
            title="This plan isn't connected yet"
            description="prem3-api doesn't have a plan detail endpoint deployed yet (docs/contracts/BACKEND_REQUESTS.md REQ-010). This page is wired and ready for when it does."
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

  const plan = result.data;

  const listSections: { title: string; items: string[] }[] = [
    { title: "Recommended data sources", items: plan.recommendedSources },
    { title: "Provider / export requirements", items: plan.providerExportRequirements },
    { title: "Fields / metrics to collect", items: plan.fieldsToCollect },
    { title: "Controls / confounders to consider", items: plan.controlsConfounders },
    { title: "Known gaps", items: plan.knownGaps },
    { title: "Next actions", items: plan.nextActions },
  ];

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Acquisition plan"
        subtitle={`${plan.provenanceLabel} · Plan v${plan.planVersion} · ${plan.generatedAtLabel}`}
        backHref={routes.workspacePlans(workspaceId)}
        backLabel="Back to planning"
      />

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-prem3-navy">
          <ClipboardList className="size-4 text-prem3-indigo" aria-hidden="true" />
          Project objective
        </h2>
        <p className="text-sm text-prem3-navy">{plan.objective}</p>
      </section>

      {listSections.map((section) => (
        <section key={section.title} className="rounded-lg border border-prem3-cool-gray bg-white p-5">
          <h2 className="mb-3 text-sm font-medium text-prem3-navy">{section.title}</h2>
          {section.items.length === 0 ? (
            <p className="text-sm text-muted-foreground">None.</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm text-prem3-navy">
              {section.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </section>
      ))}

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 text-sm font-medium text-prem3-navy">History / grain guidance</h2>
        <p className="text-sm text-muted-foreground">{plan.historyGrainGuidance ?? "Not yet available."}</p>
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="mb-3 text-sm font-medium text-prem3-navy">Owner</h2>
        <p className="text-sm text-muted-foreground">{plan.ownerLabel ?? "Not yet assigned."}</p>
      </section>
    </div>
  );
}
