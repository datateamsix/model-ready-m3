import Link from "next/link";
import { Section, Eyebrow } from "@/components/prem3/marketing-section";
import { PricingCard } from "@/components/prem3/pricing-card";
import { planCatalogSource } from "@/lib/adapters/fixture-plan-catalog-source";
import { routes } from "@/lib/routes";

const INCLUDED_IN_EVERY_PROJECT = [
  "Mapping and readiness assessment",
  "Safe, deterministic remediation",
  "Official Meridian EDA",
  "Model-ready validation",
  "BigQuery publish and verification",
  "Meridian Integration",
];

const FAQ = [
  {
    question: "What counts as an active MMM Project?",
    answer:
      "Any MMM Project you haven't archived. Your plan's limit (1, 10, or 50) applies to active Projects only.",
  },
  {
    question: "How many Datasets can a Project hold?",
    answer:
      "As many as your MMM Project needs. Datasets aren't billed or counted against your plan — only active Projects are.",
  },
  {
    question: "Are re-evaluations really unlimited?",
    answer:
      "Yes, on every paid plan. Re-running an evaluation on an existing Dataset never counts against a quota. Backend abuse and rate protections still apply.",
  },
  {
    question: "Can I cancel?",
    answer: "Yes. Manage or cancel your subscription any time from your billing settings.",
  },
  {
    question: "What happens to an archived Project?",
    answer: "It stops counting against your active Project limit. Its Datasets and evaluation history stay intact.",
  },
  {
    question: "What is Meridian Integration?",
    answer:
      "The verified handoff PreM3 produces once a Dataset is proven ready: a validated BigQuery model artifact, the official Meridian EDA report, and the full evidence trail behind every fix.",
  },
];

export default async function Page() {
  const plans = await planCatalogSource.listPlans();

  return (
    <div className="flex flex-col">
      <Section tone="light">
        <Eyebrow>Pricing</Eyebrow>
        <h1 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-3xl font-semibold text-prem3-navy sm:text-4xl">
          Priced by active MMM Projects, not by how often you check your data.
        </h1>
        <p className="mt-4 max-w-2xl text-sm text-muted-foreground">
          One project to a full portfolio. Every paid plan includes unlimited re-evaluations —
          the commercial unit is the Project, never the run.
        </p>
      </Section>

      <Section>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {plans.map((plan) => (
            <PricingCard key={plan.planId} plan={plan} />
          ))}
        </div>
      </Section>

      <Section tone="light">
        <Eyebrow>Included in every paid MMM Project</Eyebrow>
        <h2 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
          The same verified workflow, at every tier.
        </h2>
        <ul className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {INCLUDED_IN_EVERY_PROJECT.map((item) => (
            <li key={item} className="rounded-md border border-prem3-cool-gray bg-white px-4 py-3 text-sm text-prem3-navy">
              {item}
            </li>
          ))}
        </ul>
      </Section>

      <Section>
        <Eyebrow>Definitions</Eyebrow>
        <h2 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
          Project, Dataset, and Re-evaluation, precisely.
        </h2>
        <dl className="mt-8 grid gap-6 sm:grid-cols-3">
          <div>
            <dt className="font-[family-name:var(--font-display)] text-sm font-semibold text-prem3-navy">
              MMM Project
            </dt>
            <dd className="mt-1 text-sm text-muted-foreground">
              One company, client, brand, or coherent MMM program. This is what your plan counts.
            </dd>
          </div>
          <div>
            <dt className="font-[family-name:var(--font-display)] text-sm font-semibold text-prem3-navy">
              Dataset
            </dt>
            <dd className="mt-1 text-sm text-muted-foreground">
              A durable, model-input configuration inside a Project. Never billed or counted.
            </dd>
          </div>
          <div>
            <dt className="font-[family-name:var(--font-display)] text-sm font-semibold text-prem3-navy">
              Re-evaluation
            </dt>
            <dd className="mt-1 text-sm text-muted-foreground">
              One assessment of a Dataset, re-run as many times as you need. Unlimited on every paid plan.
            </dd>
          </div>
        </dl>
      </Section>

      <Section tone="light">
        <Eyebrow>FAQ</Eyebrow>
        <h2 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy sm:text-3xl">
          Questions about the plan, answered plainly.
        </h2>
        <dl className="mt-8 flex flex-col gap-6">
          {FAQ.map(({ question, answer }) => (
            <div key={question}>
              <dt className="text-sm font-semibold text-prem3-navy">{question}</dt>
              <dd className="mt-1 text-sm text-muted-foreground">{answer}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section>
        <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-prem3-navy">Not ready to pick a plan? Try the free Planner first.</p>
          <Link
            href={routes.planner()}
            className="rounded-md border border-prem3-indigo bg-prem3-indigo px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
          >
            Plan my MMM
          </Link>
        </div>
      </Section>
    </div>
  );
}
