"use client";

import Link from "next/link";
import {
  FileText,
  Search,
  Database,
  Plug,
  Cable,
  Network,
  Gavel,
  FolderKanban,
  ArrowRight,
} from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

function CtaLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
    >
      {children}
      <ArrowRight aria-hidden="true" className="h-4 w-4" />
    </Link>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-12 text-center">
      {icon && (
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-surface-secondary text-text-tertiary">
          {icon}
        </div>
      )}
      <h3 className="mb-1 text-sm font-semibold text-text">{title}</h3>
      {description && (
        <p className="mx-auto max-w-md text-sm text-text-secondary">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function EmptyDashboard() {
  return (
    <EmptyState
      icon={<Plug className="h-6 w-6" />}
      title="Dein Wissenssystem wartet auf dich"
      description="Verbinde deine erste Datenquelle, und PWBS erstellt dir automatisch ein t\u00e4gliches Kontextbriefing f\u00fcr deinen Arbeitstag."
      action={<CtaLink href="/connectors">Erste Quelle verbinden</CtaLink>}
    />
  );
}

export function EmptyBriefings() {
  return (
    <EmptyState
      icon={<FileText className="h-6 w-6" />}
      title="Noch keine Briefings erstellt"
      description="Briefings werden automatisch jeden Morgen generiert, sobald du mindestens eine Datenquelle verbunden hast. Du kannst auch jederzeit manuell ein Briefing anfordern."
      action={<CtaLink href="/connectors">Datenquelle verbinden</CtaLink>}
    />
  );
}

export function EmptyConnectors() {
  return (
    <EmptyState
      icon={<Cable className="h-6 w-6" />}
      title="Verbinde deine Werkzeuge mit PWBS"
      description="PWBS kann Daten aus Google Calendar, Notion, Zoom und Obsidian importieren. Je mehr Quellen du verbindest, desto hilfreicher werden deine Briefings und die Suche."
    />
  );
}

export function EmptySearch() {
  return (
    <EmptyState
      icon={<Search className="h-6 w-6" />}
      title="Keine Ergebnisse gefunden"
      description="Versuche es mit anderen Begriffen oder weniger spezifischen Filtern. PWBS durchsucht alle deine verbundenen Quellen semantisch \u2013 stelle deine Frage gerne in nat\u00fcrlicher Sprache."
    />
  );
}

export function EmptySearchNoDocuments() {
  return (
    <EmptyState
      icon={<Search className="h-6 w-6" />}
      title="Noch keine Dokumente vorhanden"
      description="Verbinde eine Datenquelle, damit PWBS deine Inhalte indexieren und durchsuchbar machen kann. Die Suche wird automatisch aktiv, sobald deine ersten Dokumente verarbeitet sind."
      action={<CtaLink href="/connectors">Datenquelle verbinden</CtaLink>}
    />
  );
}

export function EmptyDocuments() {
  return (
    <EmptyState
      icon={<FileText className="h-6 w-6" />}
      title="Noch keine Dokumente"
      description="Verbinde eine Datenquelle, um Dokumente zu importieren."
      action={<CtaLink href="/connectors">Datenquelle verbinden</CtaLink>}
    />
  );
}

export function EmptyEntities() {
  return (
    <EmptyState
      icon={<Network className="h-6 w-6" />}
      title="Dein Wissensgraph entsteht automatisch"
      description="Sobald PWBS Dokumente verarbeitet, erkennt es automatisch Personen, Projekte und Themen und verkn\u00fcpft sie miteinander. Verbinde weitere Quellen, um ein reicheres Wissensnetz aufzubauen."
      action={<CtaLink href="/connectors">Quellen verwalten</CtaLink>}
    />
  );
}

export function EmptyDecisions() {
  return (
    <EmptyState
      icon={<Gavel className="h-6 w-6" />}
      title="Noch keine Entscheidungen erfasst"
      description="PWBS extrahiert Entscheidungen aus deinen Meeting-Transkripten und Notizen. Verbinde Zoom oder Notion, um Entscheidungen automatisch zu erkennen."
      action={<CtaLink href="/connectors">Datenquelle verbinden</CtaLink>}
    />
  );
}

export function EmptyProjects() {
  return (
    <EmptyState
      icon={<FolderKanban className="h-6 w-6" />}
      title="Noch keine Projekte erkannt"
      description="PWBS erkennt Projekte automatisch aus deinen Datenquellen. Verbinde Google Calendar und Notion, um Projekte und ihre Zusammenh\u00e4nge zu entdecken."
      action={<CtaLink href="/connectors">Datenquelle verbinden</CtaLink>}
    />
  );
}
