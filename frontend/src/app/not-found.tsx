import Link from "next/link";
import { SearchX } from "lucide-react";
import { EmptyState } from "@/components/prem3/empty-state";
import { routes } from "@/lib/routes";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-prem3-light-gray px-6">
      <EmptyState
        icon={SearchX}
        title="Page not found"
        description="The page you're looking for doesn't exist."
      />
      <Link href={routes.home()} className="text-sm font-medium text-prem3-indigo hover:underline">
        Back to home
      </Link>
    </div>
  );
}
