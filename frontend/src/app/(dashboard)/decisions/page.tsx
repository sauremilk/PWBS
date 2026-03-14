"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useDecisions } from "@/hooks/use-decisions";
import { DecisionList } from "@/components/decisions/decision-list";
import { Spinner } from "@/components/ui/loading-states";
import { ErrorCard } from "@/components/ui/error-states";
import type { DecisionStatus } from "@/types/api";

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Alle" },
  { value: "pending", label: "Ausstehend" },
  { value: "made", label: "Entschieden" },
  { value: "revised", label: "Revidiert" },
];

const PAGE_SIZE = 20;

export default function DecisionsPage() {
  const searchParams = useSearchParams();
  const initialStatus = searchParams.get("status") ?? "";
  const initialPage = Math.max(1, Number(searchParams.get("page")) || 1);

  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [page, setPage] = useState(initialPage);

  const { data, isLoading, error, refetch } = useDecisions({
    status: statusFilter || undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Entscheidungen</h1>

      {/* Status Filter Tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => {
              setStatusFilter(f.value);
              setPage(1);
            }}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
              statusFilter === f.value
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : error ? (
        <ErrorCard
          message="Entscheidungen konnten nicht geladen werden."
          onRetry={() => refetch()}
        />
      ) : data ? (
        <DecisionList
          decisions={data.decisions}
          total={data.total}
          page={page}
          pageSize={PAGE_SIZE}
          onPageChange={setPage}
        />
      ) : null}
    </div>
  );
}
