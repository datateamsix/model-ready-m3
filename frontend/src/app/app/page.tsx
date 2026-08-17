import { AlertTriangle, Compass, FolderPlus, Inbox } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/prem3/empty-state";
import { PlanBadge } from "@/components/prem3/plan-badge";
import { CreateProjectForm } from "@/components/prem3/create-project-form";
import { billingSource } from "@/lib/adapters/api-billing-source";
import { planCatalogSource } from "@/lib/adapters/fixture-plan-catalog-source";
import { projectSource } from "@/lib/adapters/api-project-source";
import { routes } from "@/lib/routes";

/**
 * M2-11: replaces the Mission 1-style raw-run console with a customer
 * dashboard aligned to the subscription model -- plan, active Project
 * usage, and MMM Projects as the core object, not a run list. No vanity
 * metric here is invented; every figure comes from billingSource (M2-07,
 * real) or projectSource (REQ-016, not built yet -- honest 503 gap, same
 * documented-gap pattern as billing/page.tsx).
 */
const ERROR_MESSAGES: Record<string, string> = {
  PREM3_API_TIMEOUT: "Your dashboard didn't respond in time. Try again in a moment.",
  PREM3_API_UNREACHABLE: "Couldn't reach your dashboard right now. Try again in a moment.",
  UNAUTHENTICATED: "Your session expired. Sign in again.",
};

export default async function Page() {
  const [summaryResult, plans] = await Promise.all([billingSource.getBillingSummary(), planCatalogSource.listPlans()]);

  if (!summaryResult.ok) {
    return summaryResult.status === 503 ? (
      <EmptyState
        icon={Compass}
        title="Dashboard isn't connected yet"
        description="prem3-api doesn't have an identity/entitlement endpoint deployed yet (docs/contracts/BACKEND_REQUESTS.md REQ-003). This page is wired and ready for when it does."
      />
    ) : (
      <div
        role="alert"
        className="flex items-start gap-3 rounded-md border border-prem3-cool-gray bg-white px-4 py-3 text-sm text-prem3-navy"
      >
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-prem3-navy/60" aria-hidden="true" />
        <p>{ERROR_MESSAGES[summaryResult.error.code] ?? summaryResult.error.message}</p>
      </div>
    );
  }

  const summary = summaryResult.data;
  const atLimit = summary.activeProjectCount >= summary.maxActiveProjects;
  const noSlot = summary.maxActiveProjects === 0;
  const projectsResult = await projectSource.listProjects();

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold text-prem3-navy">
            Your MMM Projects
          </h1>
          <div className="mt-2 flex items-center gap-3">
            <PlanBadge
              plan={{
                planId: summary.plan,
                displayName: plans.find((plan) => plan.planId === summary.plan)?.displayName ?? summary.plan,
                maxActiveProjects: summary.maxActiveProjects,
              }}
            />
            <span className="text-sm text-muted-foreground">
              {summary.activeProjectCount} of {summary.maxActiveProjects} active MMM Projects
            </span>
          </div>
        </div>
        {(atLimit || noSlot) && (
          <Link
            href={routes.pricing()}
            className="rounded-md bg-prem3-indigo px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
          >
            {noSlot ? "Choose a plan" : "Upgrade"}
          </Link>
        )}
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-prem3-navy/70">Recent project activity</h2>
        {!projectsResult.ok ? (
          <EmptyState
            icon={FolderPlus}
            title="Project list isn't connected yet"
            description="prem3-api doesn't have a Project endpoint deployed yet (docs/contracts/BACKEND_REQUESTS.md REQ-016). Create MMM Project below is wired and ready for when it does."
          />
        ) : projectsResult.data.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="No MMM Projects yet"
            description="Create one below, or run the free Planner first if you haven't figured out your data yet."
          />
        ) : (
          <ul className="flex flex-col gap-2">
            {projectsResult.data.map((project) => (
              <li key={project.workspaceId}>
                <Link
                  href={routes.workspace(project.workspaceId)}
                  className="flex items-center justify-between gap-3 rounded-lg border border-prem3-cool-gray bg-white px-4 py-3 transition-colors hover:border-prem3-indigo"
                >
                  <div>
                    <p className="text-sm font-medium text-prem3-navy">{project.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {project.datasetCount} dataset{project.datasetCount === 1 ? "" : "s"}
                      {project.latestActivityLabel ? ` · ${project.latestActivityLabel}` : ""}
                    </p>
                  </div>
                  <span className="text-xs font-medium text-prem3-navy/60">{project.status}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        {!noSlot && !atLimit && <CreateProjectForm />}
        <div className="flex flex-col gap-2 rounded-lg border border-dashed border-prem3-cool-gray bg-white p-5">
          <p className="text-sm font-medium text-prem3-navy">Haven&apos;t collected your data yet?</p>
          <p className="text-sm text-muted-foreground">
            Run the free Planner to find out what you&apos;ll need before starting an MMM Project.
          </p>
          <Link
            href={routes.planner()}
            className="mt-1 w-fit rounded-md border border-prem3-cool-gray px-4 py-2 text-sm font-medium text-prem3-navy transition-colors hover:bg-prem3-light-gray"
          >
            Run the free Planner
          </Link>
        </div>
      </section>

      <section className="flex flex-col gap-3 border-t border-prem3-cool-gray pt-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-prem3-navy/70">
          See PreM3&apos;s pipeline in action
        </h2>
        <Link
          href={routes.publicDemoRun("music-center-dataset-a-demo")}
          className="flex items-center justify-between gap-3 rounded-lg border border-dashed border-prem3-cool-gray bg-white px-4 py-3 transition-colors hover:border-prem3-indigo"
        >
          <div>
            <p className="text-sm font-medium text-prem3-navy">Music Center — Dataset A</p>
            <p className="text-xs text-muted-foreground">
              Fixture-backed walkthrough of the full Map/Mend/Model pipeline, not your data
            </p>
          </div>
          <span className="text-xs font-medium text-prem3-navy/60">View demo</span>
        </Link>
      </section>
    </div>
  );
}
