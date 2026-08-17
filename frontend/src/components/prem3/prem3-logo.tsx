import Image from "next/image";
import { cn } from "@/lib/utils";

const SIZE_PX: Record<"sm" | "md" | "lg", number> = {
  sm: 28,
  md: 40,
  lg: 72,
};

const WORDMARK_TEXT_CLASSES: Record<"sm" | "md" | "lg", string> = {
  sm: "text-sm",
  md: "text-lg",
  lg: "text-3xl",
};

// The approved icon-only mark (brand/brand-assets/reference/prem3-approved-icon-reference.png)
// is 385x265px, not square. Squishing it into an equal width/height box (an
// earlier bug here) distorted the mark and triggered a Next.js aspect-ratio
// console warning. Deriving height from the real intrinsic ratio keeps the
// mark undistorted at every size.
const ICON_ASPECT_RATIO = 385 / 265;

export interface PreM3LogoProps {
  size?: "sm" | "md" | "lg";
  showWordmark?: boolean;
  className?: string;
}

// Just the cube mark plus the "PreM3" wordmark -- no tagline. public/brand/prem3-icon.png
// is a transparent-background derivative of the approved icon reference (the
// source asset is a flat white RGB PNG with no alpha) so this reads correctly
// on any surface, not only white/light-gray backgrounds.
export function PreM3Logo({ size = "md", showWordmark = false, className }: PreM3LogoProps) {
  const width = SIZE_PX[size];
  const height = Math.round(width / ICON_ASPECT_RATIO);
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <Image
        src="/brand/prem3-icon.png"
        alt="PreM3"
        width={width}
        height={height}
        priority
        className="shrink-0"
      />
      {showWordmark && (
        <span
          className={cn(
            "font-[family-name:var(--font-display)] font-semibold tracking-tight text-prem3-navy",
            WORDMARK_TEXT_CLASSES[size],
          )}
        >
          PreM3
        </span>
      )}
    </div>
  );
}
