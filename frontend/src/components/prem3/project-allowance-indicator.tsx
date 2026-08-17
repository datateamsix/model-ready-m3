import { Folder } from "lucide-react";
import type { ProjectAllowanceSummary } from "@/types/ui/commercial";

/**
 * Displays the entitlement projection's used/max figures verbatim.
 * Deliberately does not render an upgrade prompt itself, even when the
 * allowance is exhausted -- that's UpgradeCta's job, composed separately
 * by the page. This component only shows status; it never decides or
 * implies what should happen next (M2-03's entitlement rule: the frontend
 * may present entitlement values, never decide whether an operation is
 * allowed).
 */
export function ProjectAllowanceIndicator({ allowance }: { allowance: ProjectAllowanceSummary }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-prem3-navy/70">
      <Folder className="size-4 text-prem3-indigo" aria-hidden="true" />
      {allowance.activeProjectCount} of {allowance.maxActiveProjects} active projects
    </span>
  );
}
