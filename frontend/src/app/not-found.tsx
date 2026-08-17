import { SearchX } from "lucide-react";
import { EmptyState } from "@/components/prem3/empty-state";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-prem3-light-gray px-6">
      <EmptyState
        icon={SearchX}
        title="Page not found"
        description="The page you're looking for doesn't exist."
      />
    </div>
  );
}
