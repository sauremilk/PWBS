"use client";

import { AlertTriangle, RefreshCw, WifiOff, ExternalLink } from "lucide-react";
import {
  resolveError,
  resolveApiError,
  type ErrorMapping,
  type ErrorAction,
} from "@/lib/error-messages";
import { ApiClientError } from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Legacy generic ErrorCard (unchanged API for backward compat)
// ---------------------------------------------------------------------------

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
    <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
      <AlertTriangle
        aria-hidden="true"
        className="mx-auto mb-3 h-8 w-8 text-red-400"
      />
      <h3 className="mb-1 text-sm font-semibold text-red-900">{title}</h3>
      <p className="text-sm text-red-700">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-surface px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
        >
          <RefreshCw aria-hidden="true" className="h-4 w-4" />
          Erneut versuchen
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MappedErrorCard - resolves error code or ApiClientError automatically
// ---------------------------------------------------------------------------

interface MappedErrorCardProps {
  code?: string | null;
  error?: unknown;
  onRetry?: () => void;
}

function renderAction(action: ErrorAction, onRetry?: () => void) {
  switch (action.type) {
    case "retry":
      if (!onRetry) return null;
      return (
        <button
          onClick={onRetry}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-surface px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
        >
          <RefreshCw aria-hidden="true" className="h-4 w-4" />
          {action.label ?? "Erneut versuchen"}
        </button>
      );
    case "link":
      return (
        <a
          href={action.href}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-surface px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
        >
          <ExternalLink aria-hidden="true" className="h-4 w-4" />
          {action.label}
        </a>
      );
    case "redirect":
      return (
        <a
          href={action.href}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-surface px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
        >
          {action.label}
        </a>
      );
  }
}

export function MappedErrorCard({ code, error, onRetry }: MappedErrorCardProps) {
  let mapped: ErrorMapping;

  if (code) {
    mapped = resolveError(code);
  } else if (error instanceof ApiClientError) {
    mapped = resolveApiError({
      status: error.status,
      data: error.data ?? undefined,
      message: error.message,
    });
  } else {
    mapped = resolveError(null);
  }

  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
      <AlertTriangle
        aria-hidden="true"
        className="mx-auto mb-3 h-8 w-8 text-red-400"
      />
      <h3 className="mb-1 text-sm font-semibold text-red-900">{mapped.title}</h3>
      <p className="text-sm text-red-700">{mapped.message}</p>
      {mapped.recovery && (
        <p className="mt-1 text-xs text-red-600">{mapped.recovery}</p>
      )}
      {mapped.action && renderAction(mapped.action, onRetry)}
    </div>
  );
}

// ---------------------------------------------------------------------------
// NetworkErrorBanner
// ---------------------------------------------------------------------------

export function NetworkErrorBanner() {
  return (
    <div
      role="alert"
      className="fixed top-0 left-0 right-0 z-50 bg-yellow-600 px-4 py-2 text-center text-sm font-medium text-white"
    >
      <WifiOff aria-hidden="true" className="mr-2 inline h-4 w-4" />
      Keine Internetverbindung. Einige Funktionen sind eingeschränkt.
    </div>
  );
}
