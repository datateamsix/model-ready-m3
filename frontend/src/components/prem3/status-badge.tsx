import { Circle, CircleCheck, CircleX, Clock, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { STATUS_LABEL, statusTone, type StatusTone } from "@/lib/format/status";
import type { PresentationStatus } from "@/types/response";

/*
 * These tones are semantic status colors layered on top of the PreM3 brand
 * palette (brand/brand-assets/tokens/prem3.tokens.json defines chrome
 * colors, not a full status ramp). Positive/warning/critical use standard
 * Tailwind semantic colors so READY vs. BLOCKED remain distinguishable
 * even before reading the label text.
 */
const TONE_CLASSES: Record<StatusTone, string> = {
  positive: "bg-emerald-50 text-emerald-800 border-emerald-200",
  warning: "bg-amber-50 text-amber-800 border-amber-200",
  critical: "bg-red-50 text-red-800 border-red-200",
  pending: "bg-prem3-cool-gray text-prem3-navy border-prem3-cool-gray",
  neutral: "bg-prem3-light-gray text-prem3-navy/70 border-prem3-cool-gray",
};

const TONE_ICON: Record<StatusTone, typeof CircleCheck> = {
  positive: CircleCheck,
  warning: TriangleAlert,
  critical: CircleX,
  pending: Clock,
  neutral: Circle,
};

export interface StatusBadgeProps {
  status: PresentationStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const tone = statusTone(status);
  const Icon = TONE_ICON[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium",
        TONE_CLASSES[tone],
        className,
      )}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  );
}
