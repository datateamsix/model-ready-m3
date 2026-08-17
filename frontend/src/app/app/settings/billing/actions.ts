"use server";

import { redirect } from "next/navigation";
import { billingSource } from "@/lib/adapters/api-billing-source";
import type { PlanId } from "@/types/ui/commercial";

/**
 * M2-07's real checkout/portal entry points. Both call the real
 * BillingSource (which fails loudly, typed, until REQ-003/REQ-013 exist --
 * see prem3-api-client.ts) and only ever redirect on a genuine backend-
 * issued redirect URL. Neither simulates a paid subscription by changing
 * client state.
 */

export interface BillingActionState {
  errorCode?: string;
  errorMessage?: string;
}

export async function startCheckoutAction(
  _prevState: BillingActionState,
  formData: FormData,
): Promise<BillingActionState> {
  const planId = formData.get("planId");
  if (typeof planId !== "string" || planId.length === 0) {
    return { errorCode: "INVALID_PLAN", errorMessage: "Choose a plan to continue." };
  }

  const result = await billingSource.createCheckoutSession(planId as PlanId);
  if (!result.ok) {
    return { errorCode: result.error.code, errorMessage: result.error.message };
  }

  redirect(result.data.redirectUrl);
}

export async function openBillingPortalAction(
  _prevState: BillingActionState,
  _formData: FormData,
): Promise<BillingActionState> {
  const result = await billingSource.createPortalSession();
  if (!result.ok) {
    return { errorCode: result.error.code, errorMessage: result.error.message };
  }

  redirect(result.data.redirectUrl);
}
