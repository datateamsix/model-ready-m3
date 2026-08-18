import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

export interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  backHref?: string;
  backLabel?: string;
}

export function PageHeader({ eyebrow, title, subtitle, actions, backHref, backLabel }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 border-b border-prem3-cool-gray pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex flex-col gap-1">
        {backHref && (
          <Link
            href={backHref}
            className="mb-1 inline-flex w-fit items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-prem3-indigo"
          >
            <ChevronLeft className="size-3.5" aria-hidden="true" />
            {backLabel ?? "Back"}
          </Link>
        )}
        {eyebrow && (
          <span className="text-xs font-medium uppercase tracking-wide text-prem3-indigo">
            {eyebrow}
          </span>
        )}
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy">
          {title}
        </h1>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
