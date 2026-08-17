import Link from "next/link";
import { Ban, CheckCircle2, ShieldCheck } from "lucide-react";
import { Section, Eyebrow } from "@/components/prem3/marketing-section";
import { routes } from "@/lib/routes";

const HIERARCHY = [
  {
    name: "MMM Project",
    description: "One company, client, brand, or coherent MMM program. Everything else lives inside it.",
  },
  {
    name: "Dataset",
    description: "A durable, model-input configuration inside a Project. A Project can hold several.",
  },
  {
    name: "Evaluation",
    description: "One assessment of a Dataset. Re-run it as many times as you need — evaluations are unlimited.",
  },
];

const PIPELINE = [
  { stage: "Map", detail: "Every source column is matched to the Meridian input schema, or flagged with an explicit question." },
  { stage: "Mend", detail: "Deterministic, auto-safe repairs fix what's broken. Anything ambiguous pauses for your review." },
  { stage: "Validate", detail: "Independent, deterministic checks confirm the repaired data actually meets the model-input contract." },
  { stage: "Meridian EDA", detail: "Official Meridian pre-modeling exploratory data analysis runs against the verified input." },
  { stage: "BigQuery", detail: "A validated, versioned model-consumption table is published and independently verified." },
  { stage: "Meridian Integration", detail: "The modeler receives the verified table, the official EDA report, and the full evidence trail." },
];

const PREM3_DECIDES = [
  "Whether a source column maps cleanly to the Meridian schema",
  "Whether a detected issue is safe to auto-repair or needs your review",
  "Whether the repaired data independently verifies against the model-input contract",
];

const MERIDIAN_REPORTS = [
  "Official pre-modeling EDA findings, severity, and text — rendered exactly as reported",
  "Whether an ERROR finding blocks the model-ready state",
  "The authoritative multicollinearity, scale, and structural checks PreM3 does not compute itself",
];

export default function Page() {
  return (
    <div className="flex flex-col">
      <Section tone="light">
        <Eyebrow>How it works</Eyebrow>
        <h1 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-3xl font-semibold text-prem3-navy sm:text-4xl">
          From fragmented data to a proven, model-ready handoff.
        </h1>
        <p className="mt-4 max-w-2xl text-sm text-muted-foreground">
          PreM3 is one coherent autonomous Taskmaster — it maps, mends, and proves your data
          is ready for Google Meridian, then hands the modeler a verified package with full
          provenance. It never fits the model itself.
        </p>
      </Section>

      <Section>
        <Eyebrow>The lifecycle</Eyebrow>
        <h2 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
          Project → Dataset → Evaluation.
        </h2>
        <ol className="mt-8 grid gap-4 sm:grid-cols-3">
          {HIERARCHY.map(({ name, description }, index) => (
            <li key={name} className="flex flex-col gap-2 rounded-lg border border-prem3-cool-gray bg-white p-5">
              <div className="flex items-center gap-2">
                <span className="flex size-6 items-center justify-center rounded-full border border-prem3-indigo text-xs font-semibold text-prem3-indigo">
                  {index + 1}
                </span>
                <span className="font-[family-name:var(--font-display)] text-base font-semibold text-prem3-navy">
                  {name}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">{description}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section tone="light">
        <Eyebrow>The pipeline</Eyebrow>
        <h2 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
          Map. Mend. Validate. Meridian EDA. BigQuery. Meridian Integration.
        </h2>
        <ol className="mt-8 flex flex-col gap-4">
          {PIPELINE.map(({ stage, detail }, index) => (
            <li key={stage} className="flex items-start gap-4 rounded-lg border border-prem3-cool-gray bg-white p-4">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full border border-prem3-indigo text-xs font-semibold text-prem3-indigo">
                {index + 1}
              </span>
              <div>
                <p className="font-[family-name:var(--font-display)] text-sm font-semibold text-prem3-navy">
                  {stage}
                </p>
                <p className="mt-0.5 text-sm text-muted-foreground">{detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section>
        <Eyebrow>Authority, kept separate</Eyebrow>
        <h2 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
          What PreM3 decides vs. what Meridian officially reports.
        </h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-2">
          <div className="rounded-lg border border-prem3-cool-gray bg-white p-5">
            <p className="flex items-center gap-2 text-sm font-semibold text-prem3-navy">
              <ShieldCheck className="size-4 text-prem3-indigo" aria-hidden="true" />
              PreM3 decides
            </p>
            <ul className="mt-3 flex flex-col gap-2">
              {PREM3_DECIDES.map((item) => (
                <li key={item} className="text-sm text-muted-foreground">
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg border border-prem3-cool-gray bg-white p-5">
            <p className="flex items-center gap-2 text-sm font-semibold text-prem3-navy">
              <CheckCircle2 className="size-4 text-prem3-indigo" aria-hidden="true" />
              Meridian officially reports
            </p>
            <ul className="mt-3 flex flex-col gap-2">
              {MERIDIAN_REPORTS.map((item) => (
                <li key={item} className="text-sm text-muted-foreground">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      <Section tone="light">
        <div className="flex items-start gap-4">
          <Ban className="mt-1 size-6 shrink-0 text-prem3-navy/60" aria-hidden="true" />
          <div className="max-w-2xl">
            <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
              What PreM3 intentionally doesn&apos;t do
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Posterior sampling and Meridian model fitting stay outside PreM3&apos;s autonomous
              authority. Official pre-modeling EDA — including EDA-only prior sampling — is
              required and is not model execution. PreM3 proves your data is ready; a modeler
              decides when and how to fit.
            </p>
          </div>
        </div>
      </Section>

      <Section>
        <div className="flex flex-wrap gap-3">
          <Link
            href={routes.planner()}
            className="rounded-md border border-prem3-indigo bg-prem3-indigo px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
          >
            Plan my MMM
          </Link>
          <Link
            href={routes.start()}
            className="rounded-md border border-prem3-cool-gray bg-white px-5 py-2.5 text-sm font-medium text-prem3-navy transition-colors hover:border-prem3-indigo"
          >
            Get started
          </Link>
        </div>
      </Section>
    </div>
  );
}
