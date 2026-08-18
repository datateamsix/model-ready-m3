import type { ReactNode } from "react";
import { SettingsNav } from "@/components/prem3/settings-nav";

/**
 * Shared shell for /app/settings/* (M2-15). Gives Account and Billing a way
 * to switch between each other -- before this, each was only reachable
 * directly by URL or via AppShell's single top-level Settings link.
 */
export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-prem3-navy">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Account identity and billing for this organization.</p>
      </div>
      <SettingsNav />
      {children}
    </div>
  );
}
