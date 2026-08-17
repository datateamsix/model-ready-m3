import Link from "next/link";
import type { ReactNode } from "react";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import { PreM3Logo } from "./prem3-logo";
import { routes } from "@/lib/routes";

const CLERK_APPEARANCE = {
  variables: { colorPrimary: "#3B4BDB" },
  elements: { userButtonAvatarBox: "size-8" },
};

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-prem3-light-gray">
      <header className="border-b border-prem3-cool-gray bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-6">
            <Link href={routes.app()} className="flex items-center gap-3">
              <PreM3Logo size="sm" showWordmark />
            </Link>
            {/* Clerk Organizations give B2B identity context: which MMM
                Project workspace's account the signed-in user is acting
                as. Switching orgs here, not a custom picker, keeps
                membership/invite management inside Clerk's own UI. */}
            <OrganizationSwitcher
              hidePersonal={false}
              appearance={CLERK_APPEARANCE}
            />
          </div>
          <nav className="flex items-center gap-6 text-sm font-medium text-prem3-navy/70">
            <Link href={routes.app()} className="transition-colors hover:text-prem3-indigo">
              Dashboard
            </Link>
            <Link href={routes.settingsBilling()} className="transition-colors hover:text-prem3-indigo">
              Billing
            </Link>
            <UserButton appearance={CLERK_APPEARANCE} />
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">{children}</main>
    </div>
  );
}
