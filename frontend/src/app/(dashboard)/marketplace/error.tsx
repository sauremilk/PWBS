"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";

export default function MarketplaceError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div
      data-testid="error-boundary"
      className="rounded-lg border border-red-200 bg-red-50 p-6 text-center"
    >
      <AlertTriangle
        aria-hidden="true"
        className="mx-auto mb-3 h-8 w-8 text-red-400"
      />
      <h3 className="mb-1 text-sm font-semibold text-red-900">
        Unerwarteter Fehler
      </h3>
      <p className="text-sm text-red-700">
        {error.message || "Etwas ist schiefgelaufen."}
      </p>
      <button
        onClick={reset}
        className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-surface px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
      >
        <RefreshCw aria-hidden="true" className="h-4 w-4" />
        Erneut versuchen
      </button>
    </div>
  );
}
