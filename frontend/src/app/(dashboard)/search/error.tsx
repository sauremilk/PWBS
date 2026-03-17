"use client";

import { MappedErrorCard } from "@/components/ui/error-states";

export default function SectionError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div data-testid="error-boundary">
      <MappedErrorCard error={error} onRetry={reset} />
    </div>
  );
}
