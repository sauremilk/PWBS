"use client";

import { useState, Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Search,
  Users,
  FolderKanban,
  Hash,
  ChevronLeft,
  ChevronRight,
  Network,
  List,
  Gavel,
  Target,
  AlertTriangle,
  Lightbulb,
  HelpCircle,
} from "lucide-react";
import { useEntities, useGraph } from "@/hooks/use-knowledge";
import { ForceGraph, GraphLegend } from "@/components/knowledge/force-graph";
import { Spinner } from "@/components/ui/loading-states";
import { ErrorCard } from "@/components/ui/error-states";
import { EmptyEntities } from "@/components/ui/empty-states";
import type { EntityListItem } from "@/types/api";

const ENTITY_TYPES = [
  { value: "", label: "Alle", icon: Hash },
  { value: "Person", label: "Personen", icon: Users },
  { value: "Project", label: "Projekte", icon: FolderKanban },
  { value: "Topic", label: "Themen", icon: Hash },
  { value: "Decision", label: "Entscheidungen", icon: Gavel },
  { value: "Goal", label: "Ziele", icon: Target },
  { value: "Risk", label: "Risiken", icon: AlertTriangle },
  { value: "Hypothesis", label: "Hypothesen", icon: Lightbulb },
  { value: "OpenQuestion", label: "Offene Fragen", icon: HelpCircle },
] as const;

const PAGE_SIZE = 20;

type ViewMode = "list" | "graph";

function KnowledgeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const initialType = searchParams.get("type") ?? "";
  const initialPage = Math.max(1, Number(searchParams.get("page")) || 1);
  const initialView = (searchParams.get("view") ?? "list") as ViewMode;

  const [typeFilter, setTypeFilter] = useState(initialType);
  const [page, setPage] = useState(initialPage);
  const [viewMode, setViewMode] = useState<ViewMode>(initialView);
  const [graphEntityId, setGraphEntityId] = useState<string | undefined>(
    searchParams.get("entity") ?? undefined,
  );
  const [graphDepth, setGraphDepth] = useState(2);

  // Entity list query
  const {
    data: entityData,
    isLoading: entitiesLoading,
    error: entitiesError,
    refetch: refetchEntities,
  } = useEntities({
    type: typeFilter || undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  // Graph query
  const {
    data: graphData,
    isLoading: graphLoading,
    error: graphError,
  } = useGraph({
    depth: graphDepth,
    entity_id: graphEntityId,
  });

  const updateUrl = useCallback(
    (params: Record<string, string>) => {
      const sp = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(params)) {
        if (v) sp.set(k, v);
        else sp.delete(k);
      }
      router.replace(`/knowledge?${sp.toString()}`);
    },
    [router, searchParams],
  );

  const handleTypeChange = (type: string) => {
    setTypeFilter(type);
    setPage(1);
    updateUrl({ type, page: "" });
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    updateUrl({ page: newPage > 1 ? String(newPage) : "" });
  };

  const handleViewChange = (mode: ViewMode) => {
    setViewMode(mode);
    updateUrl({ view: mode });
  };

  const handleGraphNodeClick = (nodeId: string) => {
    setGraphEntityId(nodeId);
    updateUrl({ entity: nodeId });
  };

  const totalPages = entityData ? Math.ceil(entityData.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Knowledge Explorer
          </h1>
          <p className="mt-1 text-gray-500">
            Entitäten, Beziehungen und Wissensgraph erkunden
          </p>
        </div>

        {/* View toggle */}
        <div className="flex items-center gap-1 rounded-lg border border-gray-200 p-1">
          <button
            onClick={() => handleViewChange("list")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              viewMode === "list"
                ? "bg-gray-900 text-white"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <List className="h-4 w-4" />
            Liste
          </button>
          <button
            onClick={() => handleViewChange("graph")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              viewMode === "graph"
                ? "bg-gray-900 text-white"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <Network className="h-4 w-4" />
            Graph
          </button>
        </div>
      </div>

      {/* ─── List View ─── */}
      {viewMode === "list" && (
        <>
          {/* Filters */}
          <div className="flex items-center gap-3">
            {ENTITY_TYPES.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => handleTypeChange(value)}
                className={`flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  typeFilter === value
                    ? "bg-gray-900 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
            {entityData && (
              <span className="ml-auto text-sm text-gray-500">
                {entityData.total} Entität{entityData.total !== 1 ? "en" : ""}
              </span>
            )}
          </div>

          {/* Entity list */}
          {entitiesLoading && (
            <div className="flex justify-center py-20">
              <Spinner className="h-8 w-8" />
            </div>
          )}

          {entitiesError && (
            <ErrorCard
              message="Entitäten konnten nicht geladen werden."
              onRetry={() => void refetchEntities()}
            />
          )}

          {entityData && entityData.entities.length === 0 && <EmptyEntities />}

          {entityData && entityData.entities.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Typ
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                      Erwähnungen
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                      Zuletzt gesehen
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {entityData.entities.map((entity: EntityListItem) => (
                    <EntityRow key={entity.id} entity={entity} />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
                className="flex items-center gap-1 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
                Zurück
              </button>
              <span className="text-sm text-gray-500">
                Seite {page} von {totalPages}
              </span>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages}
                className="flex items-center gap-1 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Weiter
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </>
      )}

      {/* ─── Graph View ─── */}
      {viewMode === "graph" && (
        <div className="space-y-4">
          {/* Graph controls */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label htmlFor="graph-depth" className="text-sm font-medium text-gray-700">
                Tiefe:
              </label>
              <select
                id="graph-depth"
                value={graphDepth}
                onChange={(e) => setGraphDepth(Number(e.target.value))}
                className="rounded-md border border-gray-300 px-2 py-1 text-sm"
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
              </select>
            </div>
            {graphEntityId && (
              <button
                onClick={() => {
                  setGraphEntityId(undefined);
                  updateUrl({ entity: "" });
                }}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Gesamten Graph anzeigen
              </button>
            )}
            <GraphLegend />
          </div>

          {/* Graph canvas */}
          {graphLoading && (
            <div className="flex justify-center py-20">
              <Spinner className="h-8 w-8" />
            </div>
          )}

          {graphError && (
            <ErrorCard message="Graph konnte nicht geladen werden." />
          )}

          {graphData && graphData.nodes.length === 0 && (
            <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
              <Network className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                Keine Graph-Daten
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                Es wurden noch keine Entitäten und Beziehungen extrahiert.
              </p>
            </div>
          )}

          {graphData && graphData.nodes.length > 0 && (
            <ForceGraph
              nodes={graphData.nodes}
              edges={graphData.edges}
              onNodeClick={handleGraphNodeClick}
              width={1000}
              height={600}
            />
          )}

          {/* Show entity info below graph when entity selected */}
          {graphEntityId && graphData && (
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">
                    {graphData.nodes.find((n) => n.id === graphEntityId)?.name ??
                      "Entität"}
                  </h3>
                  <p className="text-sm text-gray-500">
                    Typ:{" "}
                    {graphData.nodes.find((n) => n.id === graphEntityId)?.type}
                  </p>
                </div>
                <Link
                  href={`/knowledge/${encodeURIComponent(graphEntityId)}`}
                  className="rounded-md bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-800"
                >
                  Details anzeigen
                </Link>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EntityRow({ entity }: { entity: EntityListItem }) {
  const typeLabel: Record<string, string> = {
    Person: "Person",
    Project: "Projekt",
    Topic: "Thema",
    Decision: "Entscheidung",
  };

  const typeColor: Record<string, string> = {
    Person: "bg-blue-100 text-blue-800",
    Project: "bg-green-100 text-green-800",
    Topic: "bg-amber-100 text-amber-800",
    Decision: "bg-red-100 text-red-800",
  };

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-6 py-4">
        <Link
          href={`/knowledge/${encodeURIComponent(entity.id)}`}
          className="font-medium text-gray-900 hover:text-blue-600"
        >
          {entity.name}
        </Link>
      </td>
      <td className="px-6 py-4">
        <span
          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
            typeColor[entity.type] ?? "bg-gray-100 text-gray-800"
          }`}
        >
          {typeLabel[entity.type] ?? entity.type}
        </span>
      </td>
      <td className="px-6 py-4 text-right text-sm text-gray-700">
        {entity.mention_count}
      </td>
      <td className="px-6 py-4 text-right text-sm text-gray-500">
        {entity.last_seen
          ? new Date(entity.last_seen).toLocaleDateString("de-DE")
          : "–"}
      </td>
    </tr>
  );
}

export default function KnowledgePage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-20">
          <Spinner className="h-8 w-8" />
        </div>
      }
    >
      <KnowledgeContent />
    </Suspense>
  );
}
