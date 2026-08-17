import type { LucideIcon } from "lucide-react";

export interface SectionHeaderProps {
  icon: LucideIcon;
  title: string;
  count?: number;
}

export function SectionHeader({ icon: Icon, title, count }: SectionHeaderProps) {
  return (
    <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-prem3-navy/70">
      <Icon className="size-4 text-prem3-indigo" aria-hidden="true" />
      {title}
      {typeof count === "number" && (
        <span className="rounded-full bg-prem3-cool-gray px-2 py-0.5 text-xs font-medium text-prem3-navy">
          {count}
        </span>
      )}
    </h3>
  );
}
