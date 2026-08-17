"use client";

import { useActionState } from "react";
import Link from "next/link";
import { createProjectAction, type CreateProjectActionState } from "@/app/app/actions";
import { routes } from "@/lib/routes";

const INITIAL_STATE: CreateProjectActionState = {};

/**
 * M2-11: minimal creation flow -- name only, no technical dataset fields.
 * Entitlement is checked server-side; a typed PROJECT_LIMIT_REACHED maps to
 * an upgrade CTA here rather than a generic error message.
 */
export function CreateProjectForm() {
  const [state, formAction, isPending] = useActionState(createProjectAction, INITIAL_STATE);

  return (
    <form action={formAction} className="flex flex-col gap-2 rounded-lg border border-prem3-cool-gray bg-white p-5">
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium text-prem3-navy">New MMM Project</span>
        <input
          type="text"
          name="name"
          placeholder="e.g. Q3 brand campaign"
          className="rounded-md border border-prem3-cool-gray px-3 py-2 text-sm text-prem3-navy"
        />
      </label>
      <button
        type="submit"
        disabled={isPending}
        className="w-fit rounded-md bg-prem3-indigo px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Creating…" : "Create MMM Project"}
      </button>

      {state.errorCode === "PROJECT_LIMIT_REACHED" ? (
        <p className="text-xs text-prem3-navy">
          You&apos;re at your plan&apos;s active Project limit.{" "}
          <Link href={routes.pricing()} className="font-medium text-prem3-indigo underline underline-offset-2">
            Upgrade
          </Link>{" "}
          to create another.
        </p>
      ) : (
        state.errorMessage && (
          <p role="alert" className="text-xs text-red-600">
            {state.errorMessage}
          </p>
        )
      )}
    </form>
  );
}
