import { StatusBadge } from "./status-badge";
import type { PresentationStatus } from "@/types/response";

export interface StatusHeaderProps {
  title: string;
  summary: string;
  status: PresentationStatus;
}

export function StatusHeader({ title, summary, status }: StatusHeaderProps) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-prem3-cool-gray bg-white p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
          {title}
        </h2>
        <StatusBadge status={status} />
      </div>
      <p className="text-sm text-muted-foreground">{summary}</p>
    </div>
  );
}
