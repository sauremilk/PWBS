"use client";

import Link from "next/link";
import { FileText, Plus, Cable, AlertCircle, Loader2 } from "lucide-react";
import { useLatestBriefing, useGenerateBriefing } from "@/hooks/use-briefings";
import { useConnectionStatus } from "@/hooks/use-connectors";

function BriefingCard() {
  const { data: briefing, isLoading, error } = useLatestBriefing("morning");
  const generate = useGenerateBriefing();

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-gray-200 bg-white p-8"
        role="status"
      >
        <Loader2
          aria-hidden="true"
          className="h-6 w-6 animate-spin text-gray-400"
        />
        <span className="sr-only">Wird geladen</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <div className="flex items-center gap-2 text-red-700">
          <AlertCircle aria-hidden="true" className="h-5 w-5" />
          <span className="text-sm">Briefing konnte nicht geladen werden.</span>
        </div>
      </div>
    );
  }

  if (!briefing) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <p className="mb-4 text-gray-600">
          Kein aktuelles Morgenbriefing verfügbar.
        </p>
        <button
          onClick={() => generate.mutate({ type: "morning" })}
          disabled={generate.isPending}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          <Plus aria-hidden="true" className="h-4 w-4" />
          {generate.isPending ? "Generiere…" : "Briefing jetzt generieren"}
        </button>
      </div>
    );
  }

  return (
    <Link
      href={`/briefings/${briefing.id}`}
      className="block rounded-lg border border-gray-200 bg-white p-6 transition-shadow hover:shadow-md"
    >
      <div className="mb-2 flex items-center gap-2">
        <FileText aria-hidden="true" className="h-5 w-5 text-blue-600" />
        <span className="text-xs font-medium uppercase tracking-wide text-gray-500">
          Morgenbriefing
        </span>
        <span className="ml-auto text-xs text-gray-500">
          {new Date(briefing.generated_at).toLocaleString("de-DE", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
      <h2 className="text-lg font-semibold text-gray-900">{briefing.title}</h2>
    </Link>
  );
}

function ConnectorStatusWidget() {
  const { data, isLoading } = useConnectionStatus();

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-gray-900">
          Konnektoren
        </h3>
        <div className="flex items-center justify-center py-4">
          <Loader2
            aria-hidden="true"
            className="h-5 w-5 animate-spin text-gray-400"
          />
          <span className="sr-only">Wird geladen</span>
        </div>
      </div>
    );
  }

  const connections = data?.connections ?? [];

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Konnektoren</h3>
        <Link
          href="/connectors"
          className="text-xs text-blue-600 hover:text-blue-800"
        >
          Verwalten
        </Link>
      </div>
      {connections.length === 0 ? (
        <p className="text-sm text-gray-500">Keine Konnektoren verbunden.</p>
      ) : (
        <ul className="space-y-2">
          {connections.map((c) => (
            <li
              key={c.type}
              className="flex items-center justify-between text-sm"
            >
              <div className="flex items-center gap-2">
                <Cable aria-hidden="true" className="h-4 w-4 text-gray-500" />
                <span className="text-gray-700">{c.type}</span>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  c.status === "active"
                    ? "bg-green-100 text-green-700"
                    : c.status === "error"
                      ? "bg-red-100 text-red-700"
                      : "bg-gray-100 text-gray-700"
                }`}
              >
                {c.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Hauptinhalt: Briefing */}
        <div className="lg:col-span-2 space-y-4">
          <BriefingCard />
        </div>

        {/* Sidebar: Konnektor-Status */}
        <div className="space-y-4">
          <ConnectorStatusWidget />
        </div>
      </div>
    </div>
  );
}
