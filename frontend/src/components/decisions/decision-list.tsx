"use client";

import Link from "next/link";
import { Clock, CheckCircle2, RotateCcw, Plus, ChevronLeft, ChevronRight } from "lucide-react";
import type { DecisionListItem, DecisionStatus } from "@/types/api";

const STATUS_CONFIG: Record<
  DecisionStatus,
  { label: string; icon: typeof Clock; className: string }
> = {
  pending: {
    label: "Ausstehend",
    icon: Clock,
    className: "bg-yellow-100 text-yellow-800",
  },
  made: {
    label: "Entschieden",
    icon: CheckCircle2,
    className: "bg-green-100 text-green-800",
  },
  revised: {
    label: "Revidiert",
    icon: RotateCcw,
    className: "bg-blue-100 text-blue-800",
  },
};

function StatusBadge({ status }: { status: DecisionStatus }) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
    >
      <Icon className="h-3 w-3" />
      {config.label}
    </span>
  );
}

function DecisionCard({ decision }: { decision: DecisionListItem }) {
  return (
    <Link
      href={`/decisions/${decision.id}`}
      className="block rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-medium text-gray-900">
            {decision.summary}
          </h3>
          <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
            {decision.decided_by && (
              <span>von {decision.decided_by}</span>
            )}
            <span>
              {new Date(decision.created_at).toLocaleDateString("de-DE")}
            </span>
          </div>
        </div>
        <StatusBadge status={decision.status} />
      </div>
    </Link>
  );
}

interface DecisionListProps {
  decisions: DecisionListItem[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export function DecisionList({
  decisions,
  total,
  page,
  pageSize,
  onPageChange,
}: DecisionListProps) {
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {total} Entscheidung{total !== 1 ? "en" : ""}
        </p>
        <Link
          href="/decisions/new"
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          Neue Entscheidung
        </Link>
      </div>

      {decisions.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center">
          <p className="text-sm text-gray-500">
            Noch keine Entscheidungen erfasst.
          </p>
          <Link
            href="/decisions/new"
            className="mt-2 inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
          >
            <Plus className="h-4 w-4" />
            Erste Entscheidung erstellen
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {decisions.map((d) => (
            <DecisionCard key={d.id} decision={d} />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="rounded p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="text-sm text-gray-600">
            Seite {page} von {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="rounded p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  );
}
