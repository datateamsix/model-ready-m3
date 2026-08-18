import { Suspense } from "react";
import { AlertTriangle, CreditCard } from "lucide-react";
import { EmptyState } from "@/components/prem3/empty-state";
import { PlanBadge } from "@/components/prem3/plan-badge";
import { BillingActions } from "@/components/prem3/billing-actions";
import { CheckoutSuccessRefresher } from "@/components/prem3/checkout-success-refresher";
import { billingSource } from "@/lib/adapters/api-billing-source";
import { planCatalogSource } from "@/lib/adapters/fixture-plan-catalog-source";

/**
 * Known typed-error codes prem3-api-client.ts can surface get a plain-
 * language message; anything else falls back to the backend's own message
 * verbatim (still never a fabricated one).
 */
const ERROR_MESSAGES: Record<string, string> = {
  PREM3_API_TIMEOUT: "Billing didn't respond in time. Try again in a moment.",
  PREM3_API_UNREACHABLE: "Couldn't reach billing right now. Try again in a moment.",
  UNAUTHENTICATED: "Your session expired. Sign in again to view billing.",
  BILLING_PROVIDER_NOT_CONFIGURED: "Billing isn't set up for your organization yet.",
  BILLING_PROVIDER_UNAVAILABLE: "Billing is temporarily unavailable. Try again in a moment.",
  BILLING_CONFIGURATION_ERROR: "Billing is misconfigured for your organization. Contact support.",
  BILLING_CUSTOMER_UNAVAILABLE: "No billing account exists yet -- start a checkout first, or contact support.",
};

export default async function Page() {
  const [summaryResult, plans] = await Promise.all([
    billingSource.getBillingSummary(),
    planCatalogSource.listPlans(),
  ]);

  const isPending = !summaryResult.ok || summaryResult.data.plan === "planner" || summaryResult.data.planStatus !== "active";

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-xl font-semibold text-prem3-navy">Billing</h2>
        <p className="mt-1 text-sm text-muted-foreground">Plan, subscription state, and Project allowance.</p>
      </div>

      <Suspense fallback={null}>
        <CheckoutSuccessRefresher isPending={isPending} />
      </Suspense>

      {!summaryResult.ok ? (
        summaryResult.status === 503 ? (
          <EmptyState
            icon={CreditCard}
            title="Billing isn't connected yet"
            description="prem3-api doesn't have a billing endpoint deployed yet (docs/contracts/BACKEND_REQUESTS.md REQ-003, REQ-013). This page is wired and ready for when it does."
          />
        ) : (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-md border border-prem3-cool-gray bg-white px-4 py-3 text-sm text-prem3-navy"
          >
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-prem3-navy/60" aria-hidden="true" />
            <p>{ERROR_MESSAGES[summaryResult.error.code] ?? summaryResult.error.message}</p>
          </div>
        )
      ) : (
        <>
          <section className="flex flex-col gap-3 rounded-lg border border-prem3-cool-gray bg-white p-5">
            <div className="flex flex-wrap items-center gap-3">
              <PlanBadge
                plan={{
                  planId: summaryResult.data.plan,
                  displayName: plans.find((plan) => plan.planId === summaryResult.data.plan)?.displayName ?? summaryResult.data.plan,
                  maxActiveProjects: summaryResult.data.maxActiveProjects,
                }}
              />
              <span className="text-sm text-muted-foreground">
                {summaryResult.data.activeProjectCount} of {summaryResult.data.maxActiveProjects} active MMM Projects
              </span>
            </div>
            {summaryResult.data.renewsOrCancelsAtLabel && (
              <p className="text-sm text-muted-foreground">{summaryResult.data.renewsOrCancelsAtLabel}</p>
            )}
            {summaryResult.data.guidanceMessage && (
              <p className="rounded-md bg-prem3-light-gray px-3 py-2 text-sm text-prem3-navy">
                {summaryResult.data.guidanceMessage}
              </p>
            )}
          </section>

          <BillingActions plans={plans} currentPlan={summaryResult.data.plan} />
        </>
      )}
    </div>
  );
}
