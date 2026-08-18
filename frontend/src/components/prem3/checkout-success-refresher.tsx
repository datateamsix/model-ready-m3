"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

/**
 * M2-07/REQ-013: a Checkout success redirect is not proof of entitlement --
 * a refreshed `/v1/me` showing the new plan is (REQ-013's own hard rule).
 * This component never grants access or marks a plan active itself; it
 * only detects `?checkout=success` and re-triggers the Server Component
 * tree (which re-reads /v1/me through billingSource) a bounded number of
 * times with a fixed interval, so the page catches up once the backend's
 * webhook-confirmed projection lands. `isPending` is computed by the parent
 * page from the freshly re-read BillingSummary on every refresh (this
 * component holds no plan data of its own) -- while `?checkout=success` is
 * present and the plan is still pending, a "Confirming your upgrade..."
 * banner replaces the silent no-op the old version showed on every
 * refresh. After MAX_REFRESHES with no change, polling stops and a manual
 * retry action takes over rather than polling forever.
 */
const MAX_REFRESHES = 5;
const REFRESH_INTERVAL_MS = 2_000;

export function CheckoutSuccessRefresher({ isPending }: { isPending: boolean }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [exhausted, setExhausted] = useState(false);
  const attemptsRef = useRef(0);
  const checkoutStatus = searchParams.get("checkout");
  const waiting = checkoutStatus === "success" && isPending;

  useEffect(() => {
    if (!waiting || exhausted) return;

    const interval = setInterval(() => {
      attemptsRef.current += 1;
      router.refresh();
      if (attemptsRef.current >= MAX_REFRESHES) {
        clearInterval(interval);
        setExhausted(true);
      }
    }, REFRESH_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [waiting, exhausted, router]);

  function retry() {
    attemptsRef.current = 0;
    setExhausted(false);
    router.refresh();
  }

  if (!waiting) return null;

  return (
    <div
      role="status"
      className="flex items-center justify-between gap-3 rounded-md border border-prem3-cool-gray bg-prem3-light-gray px-4 py-3 text-sm text-prem3-navy"
    >
      <span className="flex items-center gap-2">
        <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
        {exhausted
          ? "Still confirming your upgrade -- this is taking longer than expected."
          : "Confirming your upgrade…"}
      </span>
      {exhausted && (
        <button
          type="button"
          onClick={retry}
          className="shrink-0 rounded-md border border-prem3-cool-gray bg-white px-3 py-1.5 text-xs font-medium text-prem3-navy transition-colors hover:bg-prem3-light-gray"
        >
          Try again
        </button>
      )}
    </div>
  );
}
