import type { LucideIcon } from "lucide-react";

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-prem3-cool-gray bg-white px-6 py-12 text-center">
      <Icon className="size-8 text-prem3-navy/30" aria-hidden="true" />
      <p className="text-sm font-medium text-prem3-navy">{title}</p>
      <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
