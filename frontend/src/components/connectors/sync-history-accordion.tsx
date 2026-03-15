"use client";

import { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  ChevronDown,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { useSyncHistory } from "@/hooks/use-connectors";
import type { SyncRunItem } from "@/types/api";

interface SyncHistoryAccordionProps {
  connectorType: string;
}

const STATUS_CONFIG: Record<
  string,
  { icon: typeof CheckCircle2; color: string; label: string }
> = {
  success: { icon: CheckCircle2, color: "text-green-500", label: "Erfolgreich" },
  failed: { icon: XCircle, color: "text-red-500", label: "Fehlgeschlagen" },
  running: { icon: Loader2, color: "text-blue-500", label: "Läuft" },
  pending: { icon: Clock, color: "text-gray-400", label: "Wartend" },
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "–";
  return new Date(dateStr).toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "–";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function RunRow({ run }: { run: SyncRunItem }) {
  const [expanded, setExpanded] = useState(false);
  const config = STATUS_CONFIG[run.status] ?? STATUS_CONFIG.pending;
  const StatusIcon = config.icon;
  const hasErrors = run.error_count > 0 && run.errors_json?.length;

  return (
    <div className="border-b border-gray-100 last:border-0 dark:border-gray-800">
      <button
        type="button"
        onClick={() => hasErrors && setExpanded(!expanded)}
        className={`flex w-full items-center gap-3 px-4 py-3 text-left text-sm transition-colors ${
          hasErrors
            ? "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50"
            : "cursor-default"
        }`}
        aria-expanded={hasErrors ? expanded : false}
      >
        <StatusIcon
          className={`h-4 w-4 flex-shrink-0 ${config.color} ${
            run.status === "running" ? "animate-spin" : ""
          }`}
        />

        <span className="flex-1 text-gray-700 dark:text-gray-300">
          {formatDate(run.started_at)}
        </span>

        <span className="flex items-center gap-1 text-xs text-gray-500">
          <FileText className="h-3.5 w-3.5" />
          {run.document_count}
        </span>

        <span className="w-16 text-right text-xs text-gray-400">
          {formatDuration(run.duration_seconds)}
        </span>

        {hasErrors ? (
          <ChevronDown
            className={`h-4 w-4 text-gray-400 transition-transform ${
              expanded ? "rotate-180" : ""
            }`}
          />
        ) : (
          <span className="w-4" />
        )}
      </button>

      {expanded && hasErrors && (
        <div className="border-t border-gray-100 bg-red-50/50 px-4 py-3 dark:border-gray-800 dark:bg-red-900/10">
          <div className="flex items-center gap-2 text-xs font-medium text-red-700 dark:text-red-400">
            <AlertTriangle className="h-3.5 w-3.5" />
            {run.error_count} Fehler
          </div>
          <ul className="mt-2 space-y-1">
            {run.errors_json!.map((err, i) => (
              <li
                key={`${err.step}-${i}`}
                className="text-xs text-red-600 dark:text-red-300"
              >
                <span className="font-mono font-medium">[{err.step}]</span>{" "}
                {err.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function SyncHistoryAccordion({
  connectorType,
}: SyncHistoryAccordionProps) {
  const { data, isLoading } = useSyncHistory(connectorType);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-6 text-sm text-gray-400">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Lade Sync-Verlauf...
      </div>
    );
  }

  if (!data || data.runs.length === 0) {
    return (
      <div className="py-6 text-center text-sm text-gray-400">
        Noch kein Sync durchgeführt
      </div>
    );
  }

  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="bg-gray-50 px-4 py-2 text-xs font-medium text-gray-500 dark:bg-gray-800/50 dark:text-gray-400">
        Letzte Syncs ({data.total} insgesamt)
      </div>
      {data.runs.map((run) => (
        <RunRow key={run.id} run={run} />
      ))}
    </div>
  );
}
