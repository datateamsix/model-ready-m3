import type { LucideIcon } from "lucide-react";
import { EmptyState } from "./empty-state";

/**
 * Mission 2's M2-01 (route namespace and final product IA) explicitly
 * scaffolds every route the final IA needs, without building the marketing
 * content, Clerk, Stripe, Planner behavior, or dataset/workspace data that
 * later prompts own. RouteStub is that placeholder: consistent visual
 * language (reuses EmptyState, not a new pattern), and each page names the
 * prompt that replaces it so a stub left in place past its owning prompt is
 * easy to spot.
 */
export function RouteStub({
  icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <EmptyState icon={icon} title={title} description={description} />
    </div>
  );
}
