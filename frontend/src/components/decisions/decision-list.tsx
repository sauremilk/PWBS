"use client";

import Link from "next/link";
import {
  Clock,
  CheckCircle2,
  RotateCcw,
  Plus,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { EmptyDecisions } from "@/components/ui/empty-states";
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
    className: "bg-indigo-100 text-indigo-800",
  },
};

function StatusBadge({ status }: { status: DecisionStatus }) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
    >
      <Icon aria-hidden="true" className="h-3 w-3" />
      {config.label}
    </span>
  );
}

function DecisionCard({ decision }: { decision: DecisionListItem }) {
  return (
    <Link
      href={`/decisions/${decision.id}`}
      className="block rounded-lg border border-border bg-surface p-4 shadow-sm transition-shadow hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-medium text-text">
            {decision.summary}
          </h3>
          <div className="mt-1 flex items-center gap-3 text-xs text-text-tertiary">
            {decision.decided_by && <span>von {decision.decided_by}</span>}
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
        <p className="text-sm text-text-tertiary">
          {total} Entscheidung{total !== 1 ? "en" : ""}
        </p>
        <Link
          href="/decisions/new"
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus aria-hidden="true" className="h-4 w-4" />
          Neue Entscheidung
        </Link>
      </div>

      {decisions.length === 0 ? (
        <EmptyDecisions />
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
            className="rounded p-1 text-text-tertiary hover:text-text-secondary disabled:opacity-30"
            aria-label="Vorherige Seite"
          >
            <ChevronLeft aria-hidden="true" className="h-5 w-5" />
          </button>
          <span className="text-sm text-text-secondary">
            Seite {page} von {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="rounded p-1 text-text-tertiary hover:text-text-secondary disabled:opacity-30"
            aria-label="Nächste Seite"
          >
            <ChevronRight aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  );
}
