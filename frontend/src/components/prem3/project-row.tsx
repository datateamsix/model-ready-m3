import Link from "next/link";
import { Archive, Database } from "lucide-react";
import { routes } from "@/lib/routes";
import type { ProjectSummary } from "@/types/ui/commercial";

/**
 * Renders only the customer-facing project name -- never workspaceId
 * (M2-03: "do not expose tenant_id in customer copy," which extends to
 * the internal workspaceId too; it stays in the href, not the visible row).
 */
export function ProjectRow({ project }: { project: ProjectSummary }) {
  return (
    <Link
      href={routes.workspace(project.workspaceId)}
      className="flex items-center justify-between gap-3 rounded-lg border border-prem3-cool-gray bg-white px-4 py-3 transition-colors hover:border-prem3-indigo"
    >
      <div className="flex items-center gap-3">
        <div>
          <p className="text-sm font-medium text-prem3-navy">{project.name}</p>
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            <Database className="size-3" aria-hidden="true" />
            {project.datasetCount} {project.datasetCount === 1 ? "dataset" : "datasets"}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        {project.latestActivityLabel && (
          <span className="text-xs text-muted-foreground">{project.latestActivityLabel}</span>
        )}
        {project.status === "ARCHIVED" && (
          <span className="flex items-center gap-1 rounded border border-prem3-cool-gray px-2 py-0.5 text-xs font-medium text-prem3-navy/60">
            <Archive className="size-3" aria-hidden="true" />
            Archived
          </span>
        )}
      </div>
    </Link>
  );
}
