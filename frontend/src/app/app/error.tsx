"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/prem3/error-state";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <ErrorState
      title="Something went wrong"
      description="An unexpected error occurred while loading this page."
      onRetry={reset}
    />
  );
}
