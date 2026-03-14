"use client";

import { AlertTriangle, RefreshCw, WifiOff } from "lucide-react";

interface ErrorCardProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorCard({
  title = "Fehler aufgetreten",
  message = "Etwas ist schiefgelaufen. Bitte versuche es erneut.",
  onRetry,
}: ErrorCardProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
      <AlertTriangle
        aria-hidden="true"
        className="mx-auto mb-3 h-8 w-8 text-red-400"
      />
      <h3 className="mb-1 text-sm font-semibold text-red-900">{title}</h3>
      <p className="text-sm text-red-700">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
        >
          <RefreshCw aria-hidden="true" className="h-4 w-4" />
          Erneut versuchen
        </button>
      )}
    </div>
  );
}

export function NetworkErrorBanner() {
  return (
    <div
      role="alert"
      className="fixed top-0 left-0 right-0 z-50 bg-yellow-600 px-4 py-2 text-center text-sm font-medium text-white"
    >
      <WifiOff aria-hidden="true" className="mr-2 inline h-4 w-4" />
      Keine Internetverbindung. Einige Funktionen sind eingeschr\u00e4nkt.
    </div>
  );
}
