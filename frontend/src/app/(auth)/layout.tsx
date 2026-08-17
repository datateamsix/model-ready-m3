import Link from "next/link";
import type { ReactNode } from "react";
import { PreM3Logo } from "@/components/prem3/prem3-logo";
import { routes } from "@/lib/routes";

/**
 * Minimal centered shell for /sign-in and /sign-up (M2-01). Real Clerk
 * integration is M2-06's scope.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-prem3-light-gray px-6">
      <Link href={routes.home()}>
        <PreM3Logo size="md" />
      </Link>
      <div className="w-full max-w-sm">{children}</div>
    </div>
  );
}
