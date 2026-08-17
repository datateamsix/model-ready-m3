import Link from "next/link";
import { Inbox } from "lucide-react";
import { PreM3Logo } from "@/components/prem3/prem3-logo";
import { EmptyState } from "@/components/prem3/empty-state";
import { preM3DataSource } from "@/lib/adapters/fixture-data-source";
import { routes } from "@/lib/routes";

const UNAVAILABLE_DEMO_ASSIGNMENTS = [
  { business: "Stride & Field", role: "Independent learning-evidence assignment (Dataset B)" },
  { business: "Summit & Pine", role: "Sealed evaluation holdout (Dataset C)" },
];

export default async function Page() {
  const runs = await preM3DataSource.listRuns();

  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-col items-start gap-4">
        <PreM3Logo size="lg" />
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold text-prem3-navy">
          PreM3
        </h1>
        <p className="max-w-xl text-sm text-muted-foreground">
          Autonomous pre-modeling for Google Meridian. Give PreM3 fragmented marketing data and it
          maps, mends, validates, publishes, and proves a model-ready BigQuery artifact.
        </p>
        <button
          type="button"
          disabled
          title="Upload orchestration is out of scope for this scaffold — see frontend/README.md"
          className="cursor-not-allowed rounded-md border border-prem3-cool-gray bg-prem3-light-gray px-4 py-2 text-sm font-medium text-prem3-navy/50"
        >
          New Assessment
        </button>
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-prem3-navy/70">Recent runs</h2>
        {runs.length === 0 ? (
          <EmptyState icon={Inbox} title="No runs yet" description="Start a new assessment to see it here." />
        ) : (
          <ul className="flex flex-col gap-2">
            {runs.map((run) => (
              <li key={run.run_id}>
                <Link
                  href={routes.publicDemoRun(run.run_id)}
                  className="flex items-center justify-between gap-3 rounded-lg border border-prem3-cool-gray bg-white px-4 py-3 transition-colors hover:border-prem3-indigo"
                >
                  <div>
                    <p className="text-sm font-medium text-prem3-navy">{run.business}</p>
                    <p className="text-xs text-muted-foreground">{run.dataset_label}</p>
                  </div>
                  <span className="text-xs font-medium text-prem3-navy/60">{run.stage}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-prem3-navy/70">Demo assignments</h2>
        <ul className="flex flex-col gap-2">
          {UNAVAILABLE_DEMO_ASSIGNMENTS.map((assignment) => (
            <li
              key={assignment.business}
              className="flex items-center justify-between gap-3 rounded-lg border border-dashed border-prem3-cool-gray bg-white px-4 py-3"
            >
              <div>
                <p className="text-sm font-medium text-prem3-navy">{assignment.business}</p>
                <p className="text-xs text-muted-foreground">{assignment.role}</p>
              </div>
              <span className="text-xs font-medium text-prem3-navy/40">
                Not yet available in this workspace
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
