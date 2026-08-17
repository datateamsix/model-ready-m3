import Link from "next/link";
import {
  Calendar,
  Coins,
  Copy,
  Layers,
  ShieldCheck,
  Tag,
} from "lucide-react";
import { Section, Eyebrow } from "@/components/prem3/marketing-section";
import { RunTimeline } from "@/components/prem3/run-timeline";
import { MeridianFindingCard } from "@/components/prem3/meridian-finding-card";
import { officialMeridianResponse } from "@/lib/fixtures/responses";
import { routes } from "@/lib/routes";

const DEFECTS = [
  { icon: Copy, label: "Duplicate rows from overlapping exports" },
  { icon: Calendar, label: "Mismatched date formats across sources" },
  { icon: Layers, label: "Daily data mixed with weekly grain" },
  { icon: Coins, label: "Spend fields stored as currency strings" },
  { icon: Tag, label: "The same channel labeled five different ways" },
];

const MAP_MEND_MODEL = [
  {
    stage: "Map",
    description:
      "Every source column gets a provable mapping to the Meridian input schema — or an explicit question, never a guess.",
  },
  {
    stage: "Mend",
    description:
      "Deterministic, auto-safe repairs fix what's broken. Anything ambiguous stops for your review before it touches the model input.",
  },
  {
    stage: "Model",
    description:
      "Not the model fit — the model-ready package: a verified BigQuery table, official Meridian EDA, and full provenance for every change.",
  },
];

const SITUATIONS = [
  {
    title: "Planning",
    description: "Haven't started collecting data yet? Find out what you'll need first.",
  },
  {
    title: "Getting organized",
    description: "Have some data, but no complete plan or dataset yet? Get it structured.",
  },
  {
    title: "Ready to assess",
    description: "Data's assembled? See exactly what's blocking a model-ready package.",
  },
];

export default function Page() {
  return (
    <div className="flex flex-col">
      <Section tone="light">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
          <div className="flex flex-col items-start gap-5">
            <Eyebrow>Autonomous pre-modeling for Google Meridian</Eyebrow>
            <h1 className="font-[family-name:var(--font-display)] text-4xl font-semibold leading-tight text-prem3-navy sm:text-5xl">
              Map the data. Mend what&apos;s broken. Prove it&apos;s model-ready.
            </h1>
            <p className="max-w-lg text-base text-muted-foreground">
              PreM3 turns fragmented marketing data into a verified, Meridian-ready BigQuery
              table — with every fix, every check, and every official finding kept separate
              and provable.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link
                href={routes.planner()}
                className="rounded-md border border-prem3-indigo bg-prem3-indigo px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
              >
                Plan my MMM
              </Link>
              <Link
                href={routes.howItWorks()}
                className="rounded-md border border-prem3-cool-gray bg-white px-5 py-2.5 text-sm font-medium text-prem3-navy transition-colors hover:border-prem3-indigo"
              >
                See how it works
              </Link>
            </div>
          </div>
          <div className="rounded-lg border border-prem3-cool-gray bg-white p-6">
            <p className="mb-4 text-xs font-medium uppercase tracking-wide text-prem3-navy/50">
              A real completed run
            </p>
            <RunTimeline currentStage="COMPLETE" failed={false} />
          </div>
        </div>
      </Section>

      <Section>
        <div className="max-w-2xl">
          <Eyebrow>Before PreM3</Eyebrow>
          <h2 className="mt-2 font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
            MMM data arrives broken in the same five ways, every time.
          </h2>
        </div>
        <ul className="mt-8 grid gap-3 sm:grid-cols-2">
          {DEFECTS.map(({ icon: Icon, label }) => (
            <li
              key={label}
              className="flex items-center gap-3 rounded-md border border-prem3-cool-gray bg-white px-4 py-3"
            >
              <Icon className="size-4 shrink-0 text-prem3-indigo" aria-hidden="true" />
              <span className="text-sm text-prem3-navy">{label}</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="light">
        <Eyebrow>Map. Mend. Model.</Eyebrow>
        <h2 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
          The operating method behind every run.
        </h2>
        <ol className="mt-8 grid gap-6 sm:grid-cols-3">
          {MAP_MEND_MODEL.map(({ stage, description }, index) => (
            <li key={stage} className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <span className="flex size-6 items-center justify-center rounded-full border border-prem3-indigo text-xs font-semibold text-prem3-indigo">
                  {index + 1}
                </span>
                <span className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
                  {stage}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">{description}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section>
        <Eyebrow>Official Meridian, kept separate</Eyebrow>
        <h2 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
          PreM3 never blends its interpretation with Meridian&apos;s official findings.
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-muted-foreground">
          Every official Meridian EDA finding renders in its own labeled block — severity and
          finding text exactly as Meridian reported them. PreM3&apos;s interpretation sits
          alongside, never merged in.
        </p>
        <div className="mt-8 max-w-xl">
          <MeridianFindingCard finding={officialMeridianResponse.official_meridian[0]} />
        </div>
      </Section>

      <Section tone="light">
        <Eyebrow>Wherever you&apos;re starting</Eyebrow>
        <h2 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
          Three ways to begin.
        </h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {SITUATIONS.map(({ title, description }) => (
            <Link
              key={title}
              href={routes.start()}
              className="flex flex-col gap-2 rounded-lg border border-prem3-cool-gray bg-white p-5 transition-colors hover:border-prem3-indigo"
            >
              <span className="font-[family-name:var(--font-display)] text-base font-semibold text-prem3-navy">
                {title}
              </span>
              <span className="text-sm text-muted-foreground">{description}</span>
            </Link>
          ))}
        </div>
      </Section>

      <Section>
        <div className="flex items-start gap-4">
          <ShieldCheck className="mt-1 size-6 shrink-0 text-prem3-indigo" aria-hidden="true" />
          <div className="max-w-2xl">
            <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
              Meridian Integration
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Meridian Integration is what PreM3 hands off once a dataset is proven ready: a
              verified BigQuery model artifact, a complete official Meridian EDA report, and the
              full evidence trail behind every fix — everything a modeler needs to fit with
              confidence.
            </p>
          </div>
        </div>
      </Section>

      <Section tone="light" slim>
        <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-prem3-navy">
            From a single MMM Project to a full portfolio.
          </p>
          <Link
            href={routes.pricing()}
            className="text-sm font-medium text-prem3-indigo hover:underline"
          >
            See pricing →
          </Link>
        </div>
      </Section>

      <Section tone="navy">
        <div className="flex flex-col items-start gap-5">
          <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-white sm:text-3xl">
            Give PreM3 the data. It completes the pre-modeling assignment.
          </h2>
          <div className="flex flex-wrap gap-3">
            <Link
              href={routes.planner()}
              className="rounded-md bg-prem3-cyan px-5 py-2.5 text-sm font-medium text-prem3-navy transition-colors hover:bg-prem3-cyan/90"
            >
              Plan my MMM
            </Link>
            <Link
              href={routes.start()}
              className="rounded-md border border-white/30 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:border-white"
            >
              Get started
            </Link>
          </div>
        </div>
      </Section>
    </div>
  );
}
