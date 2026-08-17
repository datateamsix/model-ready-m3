import Link from "next/link";
import { ArrowRight, Compass, FlaskConical, ListChecks } from "lucide-react";
import { auth } from "@clerk/nextjs/server";
import { Section, Eyebrow } from "@/components/prem3/marketing-section";
import { StartCreateProjectForm } from "@/components/prem3/start-create-project-form";
import { billingSource } from "@/lib/adapters/api-billing-source";
import { projectSource } from "@/lib/adapters/api-project-source";
import { routes } from "@/lib/routes";
import type { ProjectSummary } from "@/types/ui/commercial";
import type { StartStage } from "./actions";

/**
 * M2-09: the universal triage page. Card 1 (Planning) never touches
 * auth/backend state -- it always routes straight to the free Planner. Cards
 * 2 and 3 (Getting organized / Ready to assess) share one entitlement
 * resolution against the real BillingSource + ProjectSource: both fail
 * loudly with a typed 503 today (REQ-003/REQ-011 -- docs/contracts/
 * BACKEND_REQUESTS.md -- both NOT STARTED), which this page renders as an
 * honest blocked state rather than a fabricated project list. Nothing here
 * creates a project just from rendering the page -- only an explicit
 * StartCreateProjectForm submit does that.
 */

type EntitledState =
  | { kind: "signed_out" }
  | { kind: "blocked"; message: string }
  | { kind: "no_slot" }
  | { kind: "ready"; projects: ProjectSummary[]; canCreate: boolean };

const BLOCKED_MESSAGE =
  "Project creation isn't connected yet (docs/contracts/BACKEND_REQUESTS.md REQ-003, REQ-011). " +
  "This flow is wired and ready for when it is.";

async function resolveEntitledState(): Promise<EntitledState> {
  const { userId } = await auth();
  if (!userId) {
    return { kind: "signed_out" };
  }

  const [summaryResult, projectsResult] = await Promise.all([
    billingSource.getBillingSummary(),
    projectSource.listProjects(),
  ]);

  if (!summaryResult.ok) {
    return { kind: "blocked", message: summaryResult.status === 503 ? BLOCKED_MESSAGE : summaryResult.error.message };
  }
  if (!projectsResult.ok) {
    return { kind: "blocked", message: projectsResult.status === 503 ? BLOCKED_MESSAGE : projectsResult.error.message };
  }

  const hasSlot = summaryResult.data.activeProjectCount < summaryResult.data.maxActiveProjects;
  if (projectsResult.data.length === 0 && !hasSlot) {
    return { kind: "no_slot" };
  }

  return { kind: "ready", projects: projectsResult.data, canCreate: hasSlot };
}

function signUpHref(stage: StartStage): string {
  return `${routes.signUp()}?redirect_url=${encodeURIComponent(`${routes.start()}?stage=${stage}`)}`;
}

const CARD_CLASS = "flex flex-col gap-4 rounded-lg border border-prem3-cool-gray bg-white p-6";
const HIGHLIGHT_CLASS = "ring-2 ring-prem3-indigo";

function EntitledCardBody({
  state,
  stage,
  continueRoute,
  createLabel,
}: {
  state: EntitledState;
  stage: StartStage;
  continueRoute: (workspaceId: string) => string;
  createLabel: string;
}) {
  if (state.kind === "signed_out") {
    return (
      <>
        <p className="text-sm text-prem3-navy/80">
          This continues inside an MMM Project. Sign up (or sign in) and we&apos;ll bring you right back here.
        </p>
        <Link
          href={signUpHref(stage)}
          className="mt-auto inline-flex items-center gap-1.5 rounded-md border border-prem3-indigo bg-prem3-indigo px-4 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
        >
          Sign up to continue
          <ArrowRight className="size-3.5" aria-hidden="true" />
        </Link>
      </>
    );
  }

  if (state.kind === "blocked") {
    return <p className="text-sm text-muted-foreground">{state.message}</p>;
  }

  if (state.kind === "no_slot") {
    return (
      <>
        <p className="text-sm text-prem3-navy/80">
          This continues inside a paid MMM Project. Choose a plan to get an active Project slot.
        </p>
        <Link
          href={routes.pricing()}
          className="mt-auto inline-flex items-center gap-1.5 rounded-md border border-prem3-indigo bg-prem3-indigo px-4 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
        >
          Choose a plan
          <ArrowRight className="size-3.5" aria-hidden="true" />
        </Link>
      </>
    );
  }

  return (
    <>
      {state.projects.length > 0 && (
        <ul className="flex flex-col gap-2">
          {state.projects.map((project) => (
            <li key={project.workspaceId}>
              <Link
                href={continueRoute(project.workspaceId)}
                className="flex items-center justify-between gap-3 rounded-md border border-prem3-cool-gray px-3 py-2 text-sm text-prem3-navy transition-colors hover:border-prem3-indigo"
              >
                {project.name}
                <ArrowRight className="size-3.5 shrink-0" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      )}
      {state.canCreate ? (
        <StartCreateProjectForm stage={stage} label={createLabel} />
      ) : (
        state.projects.length > 0 && (
          <p className="text-xs text-muted-foreground">
            At your plan&apos;s Project limit —{" "}
            <Link href={routes.pricing()} className="text-prem3-indigo underline">
              upgrade
            </Link>{" "}
            to add another.
          </p>
        )
      )}
    </>
  );
}

export default async function Page({ searchParams }: { searchParams: Promise<{ stage?: string }> }) {
  const { stage: highlightedStage } = await searchParams;
  const entitledState = await resolveEntitledState();

  return (
    <div className="flex flex-col">
      <Section tone="light">
        <Eyebrow>Get started</Eyebrow>
        <h1 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-3xl font-semibold text-prem3-navy sm:text-4xl">
          Where are you starting from?
        </h1>
        <p className="mt-4 max-w-2xl text-sm text-muted-foreground">
          Pick the situation that matches where your data is today. Each path leads somewhere real —
          nothing here creates a Project or a run until you say so.
        </p>
      </Section>

      <Section>
        <div className="grid gap-6 md:grid-cols-3 md:items-start">
          <div className={CARD_CLASS}>
            <Compass className="size-6 text-prem3-indigo" aria-hidden="true" />
            <div>
              <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
                Planning
              </h2>
              <p className="mt-1 text-sm text-prem3-navy/80">I have not collected the data yet.</p>
            </div>
            <p className="text-sm text-muted-foreground">
              Find out what you&apos;ll need before you start collecting it — no account required.
            </p>
            <Link
              href={routes.planner()}
              className="mt-auto inline-flex items-center gap-1.5 rounded-md border border-prem3-indigo bg-prem3-indigo px-4 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
            >
              Start planning
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Link>
          </div>

          <div className={`${CARD_CLASS} ${highlightedStage === "getting-organized" ? HIGHLIGHT_CLASS : ""}`}>
            <ListChecks className="size-6 text-prem3-indigo" aria-hidden="true" />
            <div>
              <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
                Getting organized
              </h2>
              <p className="mt-1 text-sm text-prem3-navy/80">
                I have some data, but not a complete plan or dataset.
              </p>
            </div>
            <EntitledCardBody
              state={entitledState}
              stage="getting-organized"
              continueRoute={routes.workspacePlans}
              createLabel="Create and start planning"
            />
          </div>

          <div className={`${CARD_CLASS} ${highlightedStage === "ready-to-assess" ? HIGHLIGHT_CLASS : ""}`}>
            <FlaskConical className="size-6 text-prem3-indigo" aria-hidden="true" />
            <div>
              <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
                Ready to assess
              </h2>
              <p className="mt-1 text-sm text-prem3-navy/80">My data is assembled.</p>
            </div>
            <EntitledCardBody
              state={entitledState}
              stage="ready-to-assess"
              continueRoute={routes.workspaceDatasets}
              createLabel="Create and continue to datasets"
            />
          </div>
        </div>
      </Section>
    </div>
  );
}
