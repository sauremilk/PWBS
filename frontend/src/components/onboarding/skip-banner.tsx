"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Cable, X, ArrowRight } from "lucide-react";
import { useOnboarding } from "@/hooks/use-onboarding";
import { useConnectionStatus } from "@/hooks/use-connectors";

const DISMISS_KEY = "pwbs_skip_banner_dismissed";

/**
 * Persistenter, schließbarer Banner der nach Wizard-Skip/Abbruch auf dem
 * Dashboard angezeigt wird, solange der Nutzer keine Konnektoren hat.
 * (LAUNCH-UX-008)
 */
export function OnboardingSkipBanner() {
  const { completed } = useOnboarding();
  const { data: connectionsData } = useConnectionStatus();
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    setDismissed(localStorage.getItem(DISMISS_KEY) === "true");
  }, []);

  const handleDismiss = () => {
    localStorage.setItem(DISMISS_KEY, "true");
    setDismissed(true);
  };

  const connections = connectionsData?.connections ?? [];
  const hasConnectors = connections.some(
    (c) => c.status === "active" || c.status === "syncing",
  );

  // Don't show if: still loading, not completed, has connectors, or dismissed
  if (completed !== true || hasConnectors || dismissed) {
    return null;
  }

  return (
    <div className="mb-4 flex items-center gap-3 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3">
      <Cable aria-hidden="true" className="h-5 w-5 shrink-0 text-indigo-600" />
      <p className="flex-1 text-sm text-indigo-900">
        Verbinde deine erste Quelle, um dein Wissenssystem zu aktivieren.
      </p>
      <Link
        href="/connectors"
        className="inline-flex shrink-0 items-center gap-1 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
      >
        Jetzt verbinden
        <ArrowRight aria-hidden="true" className="h-3 w-3" />
      </Link>
      <button
        onClick={handleDismiss}
        className="shrink-0 rounded-full p-1 text-indigo-400 hover:bg-indigo-100 hover:text-indigo-600"
        aria-label="Banner schließen"
      >
        <X aria-hidden="true" className="h-4 w-4" />
      </button>
    </div>
  );
}
