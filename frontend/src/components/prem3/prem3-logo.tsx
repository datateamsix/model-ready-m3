import Image from "next/image";
import { cn } from "@/lib/utils";

const SIZE_PX: Record<"sm" | "md" | "lg", number> = {
  sm: 24,
  md: 32,
  lg: 44,
};

export interface PreM3LogoProps {
  size?: "sm" | "md" | "lg";
  showWordmark?: boolean;
  className?: string;
}

export function PreM3Logo({ size = "md", showWordmark = false, className }: PreM3LogoProps) {
  const px = SIZE_PX[size];
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <Image
        src="/brand/prem3-primary-logo.png"
        alt="PreM3"
        width={px}
        height={px}
        priority
        className="shrink-0"
      />
      {showWordmark && (
        <div className="flex flex-col leading-tight">
          <span className="font-[family-name:var(--font-display)] text-sm font-semibold tracking-tight text-prem3-navy">
            PreM3
          </span>
          <span className="text-xs uppercase tracking-wide text-prem3-navy/60">
            Map. Mend. Model.
          </span>
        </div>
      )}
    </div>
  );
}
