"use client";

import { useState } from "react";
import { Search, SlidersHorizontal, Store } from "lucide-react";
import { usePlugins } from "@/hooks/use-marketplace";
import { PluginCard } from "@/components/marketplace/plugin-card";
import { EmptyState } from "@/components/ui/empty-states";
import type { PluginType, SortField } from "@/types/marketplace";

const CATEGORY_OPTIONS: { value: PluginType | ""; label: string }[] = [
  { value: "", label: "Alle Kategorien" },
  { value: "connector", label: "Konnektoren" },
  { value: "briefing_template", label: "Briefing-Templates" },
  { value: "processing", label: "Processing" },
  { value: "agent", label: "Agenten" },
];

const SORT_OPTIONS: { value: SortField; label: string }[] = [
  { value: "popularity", label: "Beliebtheit" },
  { value: "date", label: "Neueste" },
  { value: "rating", label: "Bewertung" },
];

const PAGE_SIZE = 12;

export default function MarketplacePage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<PluginType | "">("");
  const [sort, setSort] = useState<SortField>("popularity");
  const [page, setPage] = useState(0);

  const { data, isLoading, isError } = usePlugins({
    plugin_type: category || undefined,
    search: search || undefined,
    offset: page * PAGE_SIZE,
    limit: PAGE_SIZE,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-text">Marketplace</h1>
        <div className="flex items-center gap-2">
          <SlidersHorizontal
            aria-hidden="true"
            className="h-4 w-4 text-text-tertiary"
          />
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as SortField);
              setPage(0);
            }}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-secondary"
            aria-label="Sortierung"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Search + Category Filter */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search
            aria-hidden="true"
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary"
          />
          <input
            type="search"
            placeholder="Plugins durchsuchen…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
            className="w-full rounded-md border border-border py-2 pl-9 pr-3 text-sm placeholder:text-text-tertiary focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            aria-label="Plugins durchsuchen"
          />
        </div>
        <div className="flex gap-2">
          {CATEGORY_OPTIONS.map((cat) => (
            <button
              key={cat.value}
              onClick={() => {
                setCategory(cat.value as PluginType | "");
                setPage(0);
              }}
              className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                category === cat.value
                  ? "bg-indigo-100 text-indigo-700"
                  : "bg-surface-secondary text-text-secondary hover:bg-surface-secondary"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Plugin Grid */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => (
            <div
              key={i}
              className="h-44 animate-pulse rounded-lg border border-border bg-surface-secondary"
            />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={<Store className="h-10 w-10" />}
          title="Fehler beim Laden"
          description="Die Plugin-Liste konnte nicht geladen werden."
        />
      ) : data && data.plugins.length > 0 ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.plugins.map((plugin) => (
              <PluginCard key={plugin.id} plugin={plugin} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-surface-secondary disabled:opacity-50"
              >
                Zurück
              </button>
              <span className="text-sm text-text-secondary">
                Seite {page + 1} von {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-surface-secondary disabled:opacity-50"
              >
                Weiter
              </button>
            </div>
          )}
        </>
      ) : (
        <EmptyState
          icon={<Store className="h-10 w-10" />}
          title="Keine Plugins gefunden"
          description="Versuche andere Suchbegriffe oder entferne Filter."
        />
      )}
    </div>
  );
}
