import { Section, Eyebrow } from "@/components/prem3/marketing-section";

/**
 * M2-15: production-presentable privacy policy, replacing the M2-01
 * RouteStub. Describes only the boundaries this codebase actually
 * implements today (Clerk identity, Stripe billing, server-side tenant
 * isolation via prem3-api, no browser-held GCP credentials) -- no
 * fabricated compliance certifications (SOC 2, HIPAA, etc. are not claimed
 * anywhere here because none exist yet).
 */
const SECTIONS = [
  {
    heading: "What we collect",
    body: "Account identity (name, email, organization) is managed by Clerk, our authentication provider — PreM3 never stores your password. Billing details (payment method, subscription status) are managed by Stripe — PreM3 never stores your card number. The marketing data you upload for an MMM Project (source files, mapped schema, evaluation results) is stored under your organization's isolated workspace.",
  },
  {
    heading: "How it's used",
    body: "Your account and billing data are used to authenticate you, enforce your plan's active-Project limit, and run your subscription. Your uploaded marketing data is used only to run PreM3's mapping, remediation, and validation pipeline for the MMM Project you uploaded it to, and to produce the Meridian Integration handoff. It is never used to train a shared model across organizations.",
  },
  {
    heading: "Where it's processed",
    body: "PreM3 runs on Google Cloud infrastructure. Every request is scoped server-side to your authenticated tenant and workspace — the browser never holds a Google Cloud credential, and one organization's data is never addressable from another organization's session.",
  },
  {
    heading: "Subprocessors",
    body: "Clerk (authentication and organization membership), Stripe (billing and payment processing), and Google Cloud (storage, compute, and BigQuery) process data on PreM3's behalf under their own respective privacy and security terms.",
  },
  {
    heading: "Retention and deletion",
    body: "Your data is retained for as long as your account and its MMM Projects exist. Archiving a Project stops it counting against your plan but keeps its Datasets and evaluation history intact; contact us to request full deletion of an account and its data.",
  },
  {
    heading: "Your rights",
    body: "You can review and update your account details from Account settings at any time, and manage or cancel your subscription from Billing settings. To request an export or deletion of your data, contact us using the details below.",
  },
  {
    heading: "Contact",
    body: "Questions about this policy or your data can be sent to privacy@prem3.dev.",
  },
];

export default function Page() {
  return (
    <div className="flex flex-col">
      <Section tone="light">
        <Eyebrow>Legal</Eyebrow>
        <h1 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-3xl font-semibold text-prem3-navy sm:text-4xl">
          Privacy policy
        </h1>
        <p className="mt-4 max-w-2xl text-sm text-muted-foreground">
          What PreM3 collects, how it&apos;s used, and the boundaries around your marketing data.
          Last updated August 18, 2026.
        </p>
      </Section>

      <Section>
        <dl className="flex max-w-3xl flex-col gap-8">
          {SECTIONS.map(({ heading, body }) => (
            <div key={heading}>
              <dt className="font-[family-name:var(--font-display)] text-base font-semibold text-prem3-navy">
                {heading}
              </dt>
              <dd className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</dd>
            </div>
          ))}
        </dl>
      </Section>
    </div>
  );
}
