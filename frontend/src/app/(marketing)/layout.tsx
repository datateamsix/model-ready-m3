import Link from "next/link";
import type { ReactNode } from "react";
import { PreM3Logo } from "@/components/prem3/prem3-logo";
import { routes } from "@/lib/routes";

/**
 * Minimal route-group shell for public marketing pages (M2-01). The real
 * marketing nav/hero/footer system is M2-04's scope -- this just gives
 * every marketing route a consistent, navigable shell in the meantime, and
 * a way back to the working /app console.
 */
export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="border-b border-prem3-cool-gray">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href={routes.home()} className="flex items-center gap-3">
            <PreM3Logo size="sm" showWordmark />
          </Link>
          <nav className="flex items-center gap-6 text-sm font-medium text-prem3-navy/70">
            <Link href={routes.howItWorks()} className="transition-colors hover:text-prem3-indigo">
              How it works
            </Link>
            <Link href={routes.pricing()} className="transition-colors hover:text-prem3-indigo">
              Pricing
            </Link>
            <Link href={routes.signIn()} className="transition-colors hover:text-prem3-indigo">
              Sign in
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">{children}</main>
      <footer className="border-t border-prem3-cool-gray px-6 py-6 text-xs text-muted-foreground">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4">
          <Link href={routes.pricing()} className="hover:text-prem3-indigo">
            Pricing
          </Link>
          <Link href={routes.privacy()} className="hover:text-prem3-indigo">
            Privacy
          </Link>
          <Link href={routes.terms()} className="hover:text-prem3-indigo">
            Terms
          </Link>
          <Link href={routes.signIn()} className="hover:text-prem3-indigo">
            Sign in
          </Link>
        </div>
      </footer>
    </div>
  );
}
