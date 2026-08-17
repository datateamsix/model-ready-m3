"use client";

import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import { routes } from "@/lib/routes";
import { trackPlannerEvent } from "@/lib/planner/analytics";

/**
 * M2-08 conversion CTA, shown only after a result already exists (never
 * gates the free brief itself). The entitlement check below is a real
 * authenticated call to prem3-api through the BFF -- distinct from, and
 * happening strictly after, the anonymous planning/result-generation phase
 * that must stay network-free.
 */
type ConversionState =
  | { kind: "signed_out" }
  | { kind: "checking" }
  | { kind: "no_slot" }
  | { kind: "slot_available" }
  | { kind: "at_limit" }
  | { kind: "unknown" };

interface MeResponse {
  plan: string;
  maxActiveProjects: number;
  activeProjectCount: number;
}

type MeFetchState = { kind: "loading" } | { kind: "error" } | { kind: "loaded"; data: MeResponse };

/** Pure derivation from Clerk's auth state + the fetch result -- never a
 * setState call, so there's nothing here for react-hooks/set-state-in-effect
 * to flag. The fetch effect below only ever calls setState from inside its
 * async .then/.catch callbacks, which is the pattern that rule expects. */
function deriveConversionState(isLoaded: boolean, isSignedIn: boolean | undefined, meFetch: MeFetchState): ConversionState {
  if (!isLoaded) return { kind: "checking" };
  if (!isSignedIn) return { kind: "signed_out" };
  if (meFetch.kind === "loading") return { kind: "checking" };
  if (meFetch.kind === "error") return { kind: "unknown" };

  const { data } = meFetch;
  if (data.maxActiveProjects === 0) return { kind: "no_slot" };
  if (data.activeProjectCount >= data.maxActiveProjects) return { kind: "at_limit" };
  return { kind: "slot_available" };
}

const CTA_CLASSES =
  "inline-flex items-center justify-center rounded-md bg-prem3-indigo px-4 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90";
const DISABLED_CTA_CLASSES =
  "inline-flex items-center justify-center rounded-md bg-prem3-cool-gray px-4 py-2 text-center text-sm font-medium text-prem3-navy/50";

export function PlannerConversionCta() {
  const { isSignedIn, isLoaded } = useUser();
  const [meFetch, setMeFetch] = useState<MeFetchState>({ kind: "loading" });
  const state = deriveConversionState(isLoaded, isSignedIn, meFetch);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;

    let cancelled = false;
    fetch("/api/prem3/v1/me", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) return null;
        return (await response.json()) as MeResponse;
      })
      .then((data) => {
        if (cancelled) return;
        setMeFetch(data ? { kind: "loaded", data } : { kind: "error" });
      })
      .catch(() => {
        if (!cancelled) setMeFetch({ kind: "error" });
      });

    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn]);

  function handleSaveClick() {
    trackPlannerEvent("planner_save_clicked");
    if (state.kind === "signed_out") {
      trackPlannerEvent("planner_signup_started");
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-prem3-cool-gray bg-white p-5">
      {state.kind === "signed_out" && (
        <>
          <p className="text-sm text-prem3-navy">Sign up to save this brief and turn it into a real MMM Project.</p>
          <Link
            href={`${routes.signUp()}?redirect_url=${encodeURIComponent(routes.planner())}`}
            onClick={handleSaveClick}
            className={CTA_CLASSES}
          >
            Save as an MMM Project
          </Link>
        </>
      )}

      {(state.kind === "checking" || state.kind === "unknown") && (
        <>
          <p className="text-sm text-muted-foreground">
            {state.kind === "checking" ? "Checking your account…" : "Couldn't check your plan right now."}
          </p>
          <span className={DISABLED_CTA_CLASSES} aria-disabled="true">
            Save as an MMM Project
          </span>
        </>
      )}

      {state.kind === "no_slot" && (
        <>
          <p className="text-sm text-prem3-navy">Your current plan doesn&apos;t include an MMM Project slot.</p>
          <Link href={routes.pricing()} onClick={handleSaveClick} className={CTA_CLASSES}>
            Choose a plan
          </Link>
        </>
      )}

      {state.kind === "at_limit" && (
        <>
          <p className="text-sm text-prem3-navy">You&apos;re at your plan&apos;s active Project limit.</p>
          <Link href={routes.pricing()} onClick={handleSaveClick} className={CTA_CLASSES}>
            Upgrade
          </Link>
        </>
      )}

      {state.kind === "slot_available" && (
        <>
          <p className="text-sm text-prem3-navy">You have room for another MMM Project.</p>
          <Link href={routes.app()} onClick={handleSaveClick} className={CTA_CLASSES}>
            Save as an MMM Project
          </Link>
        </>
      )}
    </div>
  );
}
