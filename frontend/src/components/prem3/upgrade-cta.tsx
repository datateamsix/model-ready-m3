import Link from "next/link";
import { ArrowUpCircle } from "lucide-react";
import { routes } from "@/lib/routes";

/**
 * Always routes to the real pricing page -- never performs a client-side
 * plan/entitlement change itself. The server remains authoritative on
 * whether an upgrade is actually needed or possible.
 */
export function UpgradeCta({ reason }: { reason: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2">
      <p className="text-sm text-amber-800">{reason}</p>
      <Link
        href={routes.pricing()}
        className="flex shrink-0 items-center gap-1.5 rounded-md border border-prem3-indigo bg-prem3-indigo px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-prem3-indigo/90"
      >
        <ArrowUpCircle className="size-3.5" aria-hidden="true" />
        Upgrade
      </Link>
    </div>
  );
}
