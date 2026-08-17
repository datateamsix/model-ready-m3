import type { ReactNode } from "react";
import { AppShell } from "@/components/prem3/app-shell";

export default function AppSegmentLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
