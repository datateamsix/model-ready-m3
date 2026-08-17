"use client";

import { useActionState } from "react";
import {
  openBillingPortalAction,
  startCheckoutAction,
  type BillingActionState,
} from "@/app/app/settings/billing/actions";
import type { PlanCatalogEntry, PlanId } from "@/types/ui/commercial";

const INITIAL_ACTION_STATE: BillingActionState = {};

/**
 * M2-07: every button here submits a Server Action that calls the real
 * BillingSource and only ever redirects on a genuine backend-issued Stripe
 * URL (see actions.ts). Nothing in this component marks a plan active or
 * changes entitlement state itself -- that only ever happens after the
 * server re-reads /v1/me.
 */
function PlanCheckoutButton({ plan }: { plan: PlanCatalogEntry }) {
  const [state, formAction, isPending] = useActionState(startCheckoutAction, INITIAL_ACTION_STATE);

  return (
    <form action={formAction} className="flex flex-col gap-1">
      <input type="hidden" name="planId" value={plan.planId} />
      <button
        type="submit"
        disabled={isPending}
        className="inline-flex items-center justify-center rounded-md bg-prem3-indigo px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Redirecting…" : plan.ctaLabel}
      </button>
      {state.errorMessage && (
        <p role="alert" className="text-xs text-red-600">
          {state.errorMessage}
        </p>
      )}
    </form>
  );
}

function ManageBillingButton() {
  const [state, formAction, isPending] = useActionState(openBillingPortalAction, INITIAL_ACTION_STATE);

  return (
    <form action={formAction} className="flex flex-col gap-1">
      <button
        type="submit"
        disabled={isPending}
        className="inline-flex items-center justify-center rounded-md border border-prem3-cool-gray bg-white px-3 py-1.5 text-sm font-medium text-prem3-navy transition-colors hover:bg-prem3-light-gray disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Opening…" : "Manage billing"}
      </button>
      {state.errorMessage && (
        <p role="alert" className="text-xs text-red-600">
          {state.errorMessage}
        </p>
      )}
    </form>
  );
}

export interface BillingActionsProps {
  plans: PlanCatalogEntry[];
  currentPlan: PlanId;
  portalAvailable: boolean;
}

export function BillingActions({ plans, currentPlan, portalAvailable }: BillingActionsProps) {
  const upgradeOptions = plans.filter((plan) => plan.stripeCheckoutAvailable && plan.planId !== currentPlan);

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-prem3-cool-gray bg-white p-5">
      {upgradeOptions.length > 0 && (
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-medium text-prem3-navy">Change plan</h2>
          <div className="flex flex-wrap gap-2">
            {upgradeOptions.map((plan) => (
              <PlanCheckoutButton key={plan.planId} plan={plan} />
            ))}
          </div>
        </div>
      )}
      {portalAvailable ? (
        <ManageBillingButton />
      ) : (
        <p className="text-sm text-muted-foreground">Manage billing isn&apos;t available yet.</p>
      )}
    </div>
  );
}
