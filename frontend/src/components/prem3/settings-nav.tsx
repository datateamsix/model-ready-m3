"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { routes } from "@/lib/routes";

const TABS = [
  { href: routes.settingsAccount(), label: "Account" },
  { href: routes.settingsBilling(), label: "Billing" },
] as const;

export function SettingsNav() {
  const pathname = usePathname();

  return (
    <nav className="flex gap-1 border-b border-prem3-cool-gray" aria-label="Settings">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={`border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              active
                ? "border-prem3-indigo text-prem3-indigo"
                : "border-transparent text-prem3-navy/60 hover:text-prem3-indigo"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
