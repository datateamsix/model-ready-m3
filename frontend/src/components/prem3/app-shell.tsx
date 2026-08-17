import Link from "next/link";
import type { ReactNode } from "react";
import { PreM3Logo } from "./prem3-logo";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-prem3-light-gray">
      <header className="border-b border-prem3-cool-gray bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-3">
            <PreM3Logo size="sm" showWordmark />
          </Link>
          <nav className="flex items-center gap-6 text-sm font-medium text-prem3-navy/70">
            <Link href="/" className="transition-colors hover:text-prem3-indigo">
              Runs
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">{children}</main>
    </div>
  );
}
