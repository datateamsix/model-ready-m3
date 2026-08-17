"use client";

import { useActionState } from "react";
import { createProjectAction, type CreateProjectActionState, type StartStage } from "@/app/(marketing)/start/actions";

const INITIAL_ACTION_STATE: CreateProjectActionState = {};

/**
 * M2-09: submits the real createProjectAction Server Action, which calls the
 * real ProjectsSource and only ever routes on a genuine backend-created
 * project (see actions.ts). Never marks a project created client-side --
 * on failure (the real state today, until REQ-011 exists) this just shows
 * the backend's typed error inline.
 */
export interface CreateProjectFormProps {
  stage: StartStage;
  label: string;
}

export function CreateProjectForm({ stage, label }: CreateProjectFormProps) {
  const [state, formAction, isPending] = useActionState(createProjectAction, INITIAL_ACTION_STATE);

  return (
    <form action={formAction} className="flex flex-col gap-2">
      <input type="hidden" name="stage" value={stage} />
      <label className="flex flex-col gap-1 text-sm font-medium text-prem3-navy">
        New MMM Project name
        <input
          type="text"
          name="name"
          required
          placeholder="e.g. Acme Q1 brand campaign"
          className="rounded-md border border-prem3-cool-gray px-3 py-1.5 text-sm text-prem3-navy focus:border-prem3-indigo focus:outline-none"
        />
      </label>
      <button
        type="submit"
        disabled={isPending}
        className="self-start rounded-md bg-prem3-indigo px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Creating…" : label}
      </button>
      {state.errorMessage && (
        <p role="alert" className="text-xs text-red-600">
          {state.errorMessage}
        </p>
      )}
    </form>
  );
}
