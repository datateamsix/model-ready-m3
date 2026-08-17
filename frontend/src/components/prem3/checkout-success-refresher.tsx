"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";

/**
 * M2-07: a Checkout success redirect is not proof of entitlement -- the
 * webhook-confirmed subscription projection is (docs/context/
 * 16_AUTH_BILLING_AND_ENTITLEMENTS.md §5.1). This component never grants
 * access or marks a plan active itself; it only detects `?checkout=success`
 * and re-triggers the Server Component tree (which re-reads /v1/me through
 * billingSource) a bounded number of times with a fixed interval, so the
 * page catches up once the backend's projection lands. It gives up after
 * MAX_REFRESHES rather than polling forever.
 */
const MAX_REFRESHES = 5;
const REFRESH_INTERVAL_MS = 2_000;

export function CheckoutSuccessRefresher() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const attemptsRef = useRef(0);
  const checkoutStatus = searchParams.get("checkout");

  useEffect(() => {
    if (checkoutStatus !== "success") return;

    const interval = setInterval(() => {
      attemptsRef.current += 1;
      router.refresh();
      if (attemptsRef.current >= MAX_REFRESHES) {
        clearInterval(interval);
      }
    }, REFRESH_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [checkoutStatus, router]);

  return null;
}
