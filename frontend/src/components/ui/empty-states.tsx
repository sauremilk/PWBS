"use client";

import { FileText, Search, Database, Plug } from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
      {icon && <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center text-gray-300">{icon}</div>}
      <h3 className="mb-1 text-sm font-semibold text-gray-900">{title}</h3>
      {description && <p className="text-sm text-gray-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function EmptyDashboard() {
  return (
    <EmptyState
      icon={<Plug className="h-10 w-10" />}
      title="Willkommen im PWBS"
      description="Verbinde deine erste Datenquelle, um loszulegen."
    />
  );
}

export function EmptySearch() {
  return (
    <EmptyState
      icon={<Search className="h-10 w-10" />}
      title="Keine Ergebnisse gefunden"
      description="Versuche andere Suchbegriffe oder entferne Filter."
    />
  );
}

export function EmptyDocuments() {
  return (
    <EmptyState
      icon={<FileText className="h-10 w-10" />}
      title="Noch keine Dokumente"
      description="Verbinde eine Datenquelle, um Dokumente zu importieren."
    />
  );
}

export function EmptyEntities() {
  return (
    <EmptyState
      icon={<Database className="h-10 w-10" />}
      title="Noch keine Entit\u00e4ten"
      description="Entit\u00e4ten werden automatisch aus importierten Dokumenten extrahiert."
    />
  );
}
