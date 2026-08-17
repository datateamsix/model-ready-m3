import { TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface ErrorStateProps {
  title: string;
  description: string;
  onRetry?: () => void;
}

export function ErrorState({ title, description, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-6 py-12 text-center">
      <TriangleAlert className="size-8 text-red-600" aria-hidden="true" />
      <p className="text-sm font-medium text-red-800">{title}</p>
      <p className="max-w-sm text-sm text-red-700/80">{description}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-2" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
