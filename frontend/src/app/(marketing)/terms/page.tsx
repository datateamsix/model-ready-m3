import { Section, Eyebrow } from "@/components/prem3/marketing-section";

/**
 * M2-15: production-presentable terms of service, replacing the M2-01
 * RouteStub. Describes the service as it's actually built (Map/Mend/Model
 * pipeline, Meridian Integration handoff, subscription billing via Stripe)
 * -- no fabricated SLAs or guarantees beyond what the product does today.
 */
const SECTIONS = [
  {
    heading: "The service",
    body: "PreM3 maps, mends, and validates your marketing data against the Meridian input schema, then hands off a verified BigQuery table, the official Meridian EDA report, and a full evidence trail — this handoff is called Meridian Integration. PreM3 never fits the Meridian model itself; posterior sampling and model fitting stay a modeler's decision.",
  },
  {
    heading: "Your account",
    body: "You're responsible for the accuracy of the data you upload and for keeping your account credentials secure. Authentication is handled by Clerk; organization membership determines which MMM Projects you can access.",
  },
  {
    heading: "Acceptable use",
    body: "You may not use PreM3 to upload data you don't have the right to process, to attempt to access another organization's workspace, or to abuse re-evaluation or API access in a way that degrades the service for others.",
  },
  {
    heading: "Billing and cancellation",
    body: "Paid plans are billed monthly through Stripe and are priced by active MMM Project count, not by run frequency — re-evaluations are unlimited on every paid plan. You can manage or cancel your subscription at any time from Billing settings; canceling stops future billing but does not delete existing Projects or data.",
  },
  {
    heading: "What PreM3 doesn't guarantee",
    body: "A model-ready package reflects that your data has passed PreM3's deterministic checks and Meridian's own official EDA — it is not a guarantee about the statistical results of a model someone later fits against that data.",
  },
  {
    heading: "Changes to these terms",
    body: "We'll update this page when the service materially changes, and note the date below.",
  },
  {
    heading: "Contact",
    body: "Questions about these terms can be sent to legal@prem3.dev.",
  },
];

export default function Page() {
  return (
    <div className="flex flex-col">
      <Section tone="light">
        <Eyebrow>Legal</Eyebrow>
        <h1 className="mt-2 max-w-2xl font-[family-name:var(--font-display)] text-3xl font-semibold text-prem3-navy sm:text-4xl">
          Terms of service
        </h1>
        <p className="mt-4 max-w-2xl text-sm text-muted-foreground">
          The terms that apply when you use PreM3. Last updated August 18, 2026.
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
