"use client";

import Link from "next/link";
import {
  FileText,
  Plus,
  Cable,
  AlertCircle,
  Search,
  FolderKanban,
  ArrowRight,
  Sparkles,
  TrendingUp,
  Clock,
  Zap,
} from "lucide-react";
import { useLatestBriefing, useGenerateBriefing } from "@/hooks/use-briefings";
import { useConnectionStatus } from "@/hooks/use-connectors";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import {
  BriefingCardSkeleton,
  ConnectorStatusSkeleton,
} from "@/components/ui/loading-states";

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
      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100">
            <Sparkles className="h-5 w-5 text-indigo-600" aria-hidden="true" />
          </div>
          <div>
            <h3 className="font-semibold text-text">Morgen-Briefing</h3>
            <p className="text-sm text-text-secondary">
              Kein aktuelles Briefing verfügbar
            </p>
          </div>
        </div>
        <button
          onClick={() => generate.mutate({ type: "morning" })}
          disabled={generate.isPending}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-indigo-600/25 hover:bg-indigo-500 disabled:opacity-50"
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
            className="mx-auto mb-2 h-8 w-8 text-text-tertiary"
            aria-hidden="true"
          />
          <p className="text-sm text-text-secondary">
            Keine Konnektoren verbunden.
          </p>
          <Link
            href="/connectors"
            className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-500"
          >
            Jetzt verbinden <ArrowRight className="h-3 w-3" />
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

function QuickActions() {
  const actions = [
    {
      href: "/briefings",
      icon: Sparkles,
      label: "Neues Briefing",
      description: "KI-Briefing generieren",
      color: "bg-indigo-100 text-indigo-600",
    },
    {
      href: "/search",
      icon: Search,
      label: "Suche",
      description: "Dokumente durchsuchen",
      color: "bg-indigo-100 text-indigo-600",
    },
    {
      href: "/connectors",
      icon: Cable,
      label: "Verbinden",
      description: "Datenquelle hinzufügen",
      color: "bg-emerald-100 text-emerald-600",
    },
    {
      href: "/projects",
      icon: FolderKanban,
      label: "Projekte",
      description: "Projekt-Briefing abrufen",
      color: "bg-amber-100 text-amber-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {actions.map((action) => (
        <Link
          key={action.href}
          href={action.href}
          className="group flex flex-col items-center gap-2 rounded-xl border border-border bg-surface p-4 text-center transition-all hover:border-indigo-200 hover:shadow-md hover:shadow-indigo-500/5"
        >
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-xl ${action.color} transition-transform group-hover:scale-110`}
          >
            <action.icon className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold text-text">{action.label}</p>
            <p className="text-xs text-text-tertiary">{action.description}</p>
          </div>
        </Link>
      ))}
    </div>
  );
}

function StatsOverview() {
  const { data } = useConnectionStatus();
  const connections = data?.connections ?? [];
  const activeCount = connections.filter((c) => c.status === "active").length;
  const totalDocs = connections.reduce((sum, c) => sum + c.doc_count, 0);

  const stats = [
    {
      label: "Konnektoren",
      value: `${activeCount}/${connections.length}`,
      icon: Zap,
      color: "text-emerald-600",
    },
    {
      label: "Dokumente",
      value: totalDocs.toLocaleString("de-DE"),
      icon: FileText,
      color: "text-indigo-600",
    },
    {
      label: "Letzte Aktivität",
      value: connections.length > 0 ? "Heute" : "–",
      icon: Clock,
      color: "text-amber-600",
    },
    {
      label: "Wissensgraph",
      value: "Aktiv",
      icon: TrendingUp,
      color: "text-indigo-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-xl border border-border bg-surface p-4"
        >
          <div className="flex items-center gap-2">
            <stat.icon className={`h-4 w-4 ${stat.color}`} aria-hidden="true" />
            <span className="text-xs font-medium text-text-secondary">
              {stat.label}
            </span>
          </div>
          <p className="mt-1 text-xl font-bold text-text">{stat.value}</p>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-text">Dashboard</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Dein persönliches Wissens-Betriebssystem auf einen Blick
        </p>
      </div>

      {/* Stats */}
      <ErrorBoundary>
        <StatsOverview />
      </ErrorBoundary>

      {/* Quick Actions */}
      <QuickActions />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <ErrorBoundary>
            <BriefingCard />
          </ErrorBoundary>
        </div>
        <div className="space-y-4">
          <ErrorBoundary>
            <ConnectorStatusWidget />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
