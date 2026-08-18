import { ChevronLeft, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "./empty-state";

/**
 * Mission 2's M2-01 (route namespace and final product IA) explicitly
 * scaffolds every route the final IA needs, without building the marketing
 * content, Clerk, Stripe, Planner behavior, or dataset/workspace data that
 * later prompts own. RouteStub is that placeholder: consistent visual
 * language (reuses EmptyState, not a new pattern), and each page names the
 * prompt that replaces it so a stub left in place past its owning prompt is
 * easy to spot. `backHref`/`backLabel` are optional so a stub nested under a
 * workspace isn't a dead end -- a stub reached from the marketing shell (which
 * already has its own nav) doesn't need one.
 */
export function RouteStub({
  icon,
  title,
  description,
  backHref,
  backLabel,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  backHref?: string;
  backLabel?: string;
}) {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4">
      {backHref && (
        <Link
          href={backHref}
          className="inline-flex items-center gap-1 self-start text-xs font-medium text-muted-foreground transition-colors hover:text-prem3-indigo"
        >
          <ChevronLeft className="size-3.5" aria-hidden="true" />
          {backLabel ?? "Back"}
        </Link>
      )}
      <EmptyState icon={icon} title={title} description={description} />
    </div>
  );
}
