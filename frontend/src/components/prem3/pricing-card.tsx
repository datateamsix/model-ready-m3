import Link from "next/link";
import { Check } from "lucide-react";
import { routes } from "@/lib/routes";
import type { PlanCatalogEntry, PlanCtaKind } from "@/types/ui/commercial";

const CTA_ROUTE: Record<PlanCtaKind, () => string> = {
  start_planner: () => routes.planner(),
  // No real Stripe checkout (REQ-013) or contact-sales page exists yet --
  // both route into the real /start funnel rather than a fabricated
  // checkout or a made-up contact address.
  start_project: () => routes.start(),
  contact_sales: () => routes.start(),
};

export function PricingCard({ plan }: { plan: PlanCatalogEntry }) {
  return (
    <div className="flex flex-col gap-4 rounded-lg border border-prem3-cool-gray bg-white p-6">
      <div>
        <p className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
          {plan.displayName}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {plan.monthlyPriceDisplay ?? "Pricing not yet configured"}
        </p>
      </div>
      <p className="text-2xl font-semibold text-prem3-navy">
        {plan.maxActiveProjects} active MMM Project{plan.maxActiveProjects === 1 ? "" : "s"}
      </p>
      <ul className="flex flex-col gap-2">
        {plan.featureSummary.map((feature) => (
          <li key={feature} className="flex items-start gap-2 text-sm text-prem3-navy/80">
            <Check className="mt-0.5 size-3.5 shrink-0 text-prem3-indigo" aria-hidden="true" />
            {feature}
          </li>
        ))}
      </ul>
      <Link
        href={CTA_ROUTE[plan.ctaKind]()}
        className="mt-auto rounded-md border border-prem3-indigo bg-prem3-indigo px-4 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
      >
        {plan.ctaLabel}
      </Link>
    </div>
  );
}
