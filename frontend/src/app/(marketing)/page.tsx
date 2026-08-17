import Link from "next/link";
import { PreM3Logo } from "@/components/prem3/prem3-logo";
import { routes } from "@/lib/routes";

/**
 * Minimal placeholder for the marketing homepage. The real hero/problem/
 * proof/pricing-teaser story is M2-04's scope -- this page exists only so
 * `/` is a real, navigable route under the Mission 2 IA (M2-01) instead of
 * still serving the Mission 1 console (which moved to /app).
 */
export default function Page() {
  return (
    <div className="flex flex-col items-start gap-6">
      <PreM3Logo size="lg" />
      <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold text-prem3-navy">
        PreM3
      </h1>
      <p className="max-w-xl text-sm text-muted-foreground">
        Autonomous pre-modeling for Google Meridian. The full marketing site lands in Mission 2
        prompt M2-04.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          href={routes.app()}
          className="rounded-md border border-prem3-indigo bg-prem3-indigo px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
        >
          Open PreM3
        </Link>
        <Link
          href={routes.pricing()}
          className="rounded-md border border-prem3-cool-gray px-4 py-2 text-sm font-medium text-prem3-navy transition-colors hover:border-prem3-indigo"
        >
          See pricing
        </Link>
      </div>
    </div>
  );
}
