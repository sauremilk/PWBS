"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  GitBranch,
  Clock,
  CheckCircle2,
  RotateCcw,
  Pencil,
  Save,
  X,
} from "lucide-react";
import { useDecisionDetail, useUpdateDecision } from "@/hooks/use-decisions";
import { Spinner } from "@/components/ui/loading-states";
import { ErrorCard } from "@/components/ui/error-states";
import type { DecisionStatus } from "@/types/api";

const STATUS_OPTIONS: {
  value: DecisionStatus;
  label: string;
  icon: typeof Clock;
}[] = [
  { value: "pending", label: "Ausstehend", icon: Clock },
  { value: "made", label: "Entschieden", icon: CheckCircle2 },
  { value: "revised", label: "Revidiert", icon: RotateCcw },
];

function ArgumentList({
  title,
  items,
  icon: Icon,
  iconColor,
}: {
  title: string;
  items: string[];
  icon: typeof ThumbsUp;
  iconColor: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-700">
        <Icon aria-hidden="true" className={`h-4 w-4 ${iconColor}`} />
        {title}
        <span className="text-xs font-normal text-gray-500">
          ({items.length})
        </span>
      </h3>
      {items.length === 0 ? (
        <p className="text-xs text-gray-500 italic">Keine Einträge</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li
              key={i}
              className="rounded-md bg-gray-50 px-3 py-2 text-sm text-gray-700"
            >
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MetadataList({
  title,
  items,
  icon: Icon,
  iconColor,
}: {
  title: string;
  items: string[];
  icon: typeof AlertTriangle;
  iconColor: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-700">
        <Icon aria-hidden="true" className={`h-4 w-4 ${iconColor}`} />
        {title}
      </h3>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-gray-600">
            &bull; {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DecisionDetail({ id }: { id: string }) {
  const router = useRouter();
  const { data: decision, isLoading, error, refetch } = useDecisionDetail(id);
  const updateMutation = useUpdateDecision(id);
  const [editingStatus, setEditingStatus] = useState(false);

  if (isLoading) {
    return (
      <div role="status" className="flex justify-center py-12">
        <Spinner />
        <span className="sr-only">Wird geladen</span>
      </div>
    );
  }

  if (error || !decision) {
    return (
      <ErrorCard
        message="Entscheidung konnte nicht geladen werden."
        onRetry={() => refetch()}
      />
    );
  }

  const handleStatusChange = async (newStatus: DecisionStatus) => {
    await updateMutation.mutateAsync({ status: newStatus });
    setEditingStatus(false);
  };

  const currentStatus = STATUS_OPTIONS.find((s) => s.value === decision.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <button
          onClick={() => router.push("/decisions")}
          className="mt-1 rounded p-1 text-gray-400 hover:text-gray-600"
          aria-label="Zurück zur Übersicht"
        >
          <ArrowLeft aria-hidden="true" className="h-5 w-5" />
        </button>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-bold text-gray-900">
            {decision.summary}
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-gray-500">
            {decision.decided_by && (
              <span>Entschieden von: {decision.decided_by}</span>
            )}
            {decision.decided_at && (
              <span>
                am {new Date(decision.decided_at).toLocaleDateString("de-DE")}
              </span>
            )}
            <span>
              Erstellt:{" "}
              {new Date(decision.created_at).toLocaleDateString("de-DE")}
            </span>
          </div>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2">
          {editingStatus ? (
            <div className="flex items-center gap-1">
              {STATUS_OPTIONS.map((opt) => {
                const OptIcon = opt.icon;
                return (
                  <button
                    key={opt.value}
                    onClick={() => handleStatusChange(opt.value)}
                    disabled={updateMutation.isPending}
                    className={`rounded-lg px-2 py-1 text-xs font-medium transition ${
                      decision.status === opt.value
                        ? "bg-blue-100 text-blue-700"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    <OptIcon
                      aria-hidden="true"
                      className="mr-1 inline h-3 w-3"
                    />
                    {opt.label}
                  </button>
                );
              })}
              <button
                onClick={() => setEditingStatus(false)}
                className="ml-1 rounded p-1 text-gray-400 hover:text-gray-600"
                aria-label="Status-Bearbeitung abbrechen"
              >
                <X aria-hidden="true" className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditingStatus(true)}
              aria-expanded={editingStatus}
              className="inline-flex items-center gap-1 rounded-lg bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200"
            >
              {currentStatus && (
                <currentStatus.icon aria-hidden="true" className="h-3 w-3" />
              )}
              {currentStatus?.label ?? decision.status}
              <Pencil
                aria-hidden="true"
                className="ml-1 h-3 w-3 text-gray-500"
              />
            </button>
          )}
        </div>
      </div>

      {/* Pro/Contra Columns */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ArgumentList
          title="Pro-Argumente"
          items={decision.pro_arguments}
          icon={ThumbsUp}
          iconColor="text-green-600"
        />
        <ArgumentList
          title="Contra-Argumente"
          items={decision.contra_arguments}
          icon={ThumbsDown}
          iconColor="text-red-500"
        />
      </div>

      {/* Assumptions & Dependencies */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <MetadataList
          title="Annahmen"
          items={decision.assumptions}
          icon={AlertTriangle}
          iconColor="text-amber-500"
        />
        <MetadataList
          title="Abh&auml;ngigkeiten"
          items={decision.dependencies}
          icon={GitBranch}
          iconColor="text-purple-500"
        />
      </div>

      {/* Timestamps */}
      <div className="text-xs text-gray-500">
        Zuletzt aktualisiert:{" "}
        {new Date(decision.updated_at).toLocaleString("de-DE")}
      </div>
    </div>
  );
}
