"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import {
  FileText,
  Cable,
  AlertCircle,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { useLatestBriefing, useGenerateBriefing } from "@/hooks/use-briefings";
import { useConnectionStatus } from "@/hooks/use-connectors";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import {
  BriefingCardSkeleton,
  ConnectorStatusSkeleton,
} from "@/components/ui/loading-states";
import { CommandBar } from "@/components/command-bar/command-bar";
import {
  SmartPrompts,
  DashboardGreeting,
} from "@/components/command-bar/smart-prompts";
import { KnowledgeProgress } from "@/components/command-bar/knowledge-progress";

function BriefingCard() {
  const { data: briefing, isLoading, error } = useLatestBriefing("morning");
  const generate = useGenerateBriefing();

  if (isLoading) {
    return <BriefingCardSkeleton />;
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6">
        <div className="flex items-center gap-2 text-red-700">
          <AlertCircle aria-hidden="true" className="h-5 w-5" />
          <span className="text-sm">Briefing konnte nicht geladen werden.</span>
        </div>
      </div>
    );
  }

  if (!briefing) {
    return (
      <div className="rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/50 to-surface p-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100">
            <Sparkles className="h-5 w-5 text-indigo-600" aria-hidden="true" />
          </div>
          <div>
            <h3 className="font-semibold text-text">
              Dein erstes Briefing wartet
            </h3>
            <p className="text-sm text-text-secondary">
              PWBS fasst dein Wissen zusammen – in 2 Sekunden generiert.
            </p>
          </div>
        </div>
        <button
          onClick={() => generate.mutate({ type: "morning" })}
          disabled={generate.isPending}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-indigo-600/25 hover:bg-indigo-500 disabled:opacity-50"
        >
          <Sparkles aria-hidden="true" className="h-4 w-4" />
          {generate.isPending ? "Generiere…" : "Jetzt ausprobieren"}
        </button>
      </div>
    );
  }

  return (
    <Link
      href={`/briefings/${briefing.id}`}
      className="group block rounded-xl border border-border bg-surface p-6 transition-all hover:border-indigo-200 hover:shadow-lg hover:shadow-indigo-500/5"
    >
      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100">
          <FileText className="h-5 w-5 text-indigo-600" aria-hidden="true" />
        </div>
        <div className="flex-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
            Morgenbriefing
          </span>
          <span className="ml-auto block text-xs text-text-tertiary sm:inline sm:ml-3">
            {new Date(briefing.generated_at).toLocaleString("de-DE", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        <ArrowRight
          className="h-4 w-4 text-text-tertiary transition-transform group-hover:translate-x-1 group-hover:text-indigo-600"
          aria-hidden="true"
        />
      </div>
      <h2 className="text-lg font-semibold text-text group-hover:text-indigo-600">
        {briefing.title}
      </h2>
    </Link>
  );
}

function ConnectorStatusWidget() {
  const { data, isLoading } = useConnectionStatus();

  if (isLoading) {
    return <ConnectorStatusSkeleton />;
  }

  const connections = data?.connections ?? [];

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cable className="h-4 w-4 text-text-secondary" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text">Konnektoren</h3>
        </div>
        <Link
          href="/connectors"
          className="text-xs font-medium text-indigo-600 hover:text-indigo-500"
        >
          Verwalten
        </Link>
      </div>
      {connections.length === 0 ? (
        <div className="py-4 text-center">
          <Cable
            className="mx-auto mb-2 h-8 w-8 text-indigo-400"
            aria-hidden="true"
          />
          <p className="text-sm font-medium text-text">Wissen verbinden</p>
          <p className="mt-1 text-xs text-text-tertiary">
            Verbinde deine erste Datenquelle und PWBS lernt dich kennen.
          </p>
          <Link
            href="/connectors"
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500"
          >
            Jetzt starten <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      ) : (
        <ul className="space-y-2.5">
          {connections.map((c) => (
            <li key={c.type} className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div
                  className={`h-2 w-2 rounded-full ${
                    c.status === "active"
                      ? "bg-emerald-500"
                      : c.status === "error"
                        ? "bg-red-500"
                        : c.status === "syncing"
                          ? "bg-indigo-500 animate-pulse"
                          : "bg-amber-500"
                  }`}
                />
                <span className="text-sm text-text">{c.type}</span>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  c.status === "active"
                    ? "bg-emerald-50 text-emerald-700"
                    : c.status === "error"
                      ? "bg-red-50 text-red-700"
                      : c.status === "syncing"
                        ? "bg-indigo-50 text-indigo-700"
                        : "bg-amber-50 text-amber-700"
                }`}
              >
                {c.status === "active"
                  ? "Aktiv"
                  : c.status === "error"
                    ? "Fehler"
                    : c.status === "syncing"
                      ? "Sync…"
                      : c.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [commandValue, setCommandValue] = useState("");
  const [promptKey, setPromptKey] = useState(0);

  const handlePromptSelect = useCallback((prompt: string) => {
    setCommandValue(prompt);
    setPromptKey((k) => k + 1);
    // Focus the command bar input after React re-renders
    requestAnimationFrame(() => {
      const input = document.querySelector<HTMLInputElement>(
        '[aria-label="PWBS Kommandozeile"]',
      );
      input?.focus();
    });
  }, []);

  return (
    <div className="space-y-6">
      {/* Greeting + Command Bar: the new center of gravity */}
      <div className="mx-auto max-w-3xl space-y-5 pt-4">
        <DashboardGreeting className="text-center" />

        <CommandBar
          key={promptKey}
          initialValue={commandValue}
          className="w-full"
        />

        <SmartPrompts
          onSelect={handlePromptSelect}
          className="flex justify-center"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <ErrorBoundary>
            <BriefingCard />
          </ErrorBoundary>
        </div>
        <div className="space-y-4">
          <ErrorBoundary>
            <KnowledgeProgress />
          </ErrorBoundary>
          <ErrorBoundary>
            <ConnectorStatusWidget />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
