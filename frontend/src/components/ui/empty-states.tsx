"use client";

import { FileText, Search, Database, Plug } from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
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
        <p className="text-sm text-text-secondary">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function EmptyDashboard() {
  return (
    <EmptyState
      icon={<Plug className="h-6 w-6" />}
      title="Willkommen im PWBS"
      description="Verbinde deine erste Datenquelle, um loszulegen."
    />
  );
}

export function EmptySearch() {
  return (
    <EmptyState
      icon={<Search className="h-6 w-6" />}
      title="Keine Ergebnisse gefunden"
      description="Versuche andere Suchbegriffe oder entferne Filter."
    />
  );
}

export function EmptyDocuments() {
  return (
    <EmptyState
      icon={<FileText className="h-6 w-6" />}
      title="Noch keine Dokumente"
      description="Verbinde eine Datenquelle, um Dokumente zu importieren."
    />
  );
}

export function EmptyEntities() {
  return (
    <EmptyState
      icon={<Database className="h-6 w-6" />}
      title="Noch keine Entit\u00e4ten"
      description="Entit\u00e4ten werden automatisch aus importierten Dokumenten extrahiert."
    />
  );
}
