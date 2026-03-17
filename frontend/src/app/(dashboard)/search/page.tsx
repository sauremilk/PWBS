"use client";

import { Suspense, useState, useCallback, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Search as SearchIcon,
  Filter,
  X,
  FileText,
  Calendar,
  Loader2,
  Bookmark,
} from "lucide-react";
import { useSearch, useCreateSavedSearch } from "@/hooks/use-search";
import { trackSearch } from "@/lib/analytics";
import { SearchCombobox } from "@/components/search/search-combobox";
import type { SearchFilters, SourceType, SearchResult } from "@/types/api";

const SOURCE_TYPE_OPTIONS: { value: SourceType; label: string }[] = [
  { value: "google_calendar", label: "Google Calendar" },
  { value: "google_drive", label: "Google Drive" },
  { value: "gmail", label: "Gmail" },
  { value: "notion", label: "Notion" },
  { value: "obsidian", label: "Obsidian" },
  { value: "zoom_transcript", label: "Zoom" },
  { value: "slack", label: "Slack" },
  { value: "outlook_mail", label: "Outlook" },
];

function ResultCard({ result }: { result: SearchResult }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 transition-all hover:border-indigo-200 hover:shadow-md hover:shadow-indigo-500/5">
      <div className="mb-2 flex items-center gap-2 text-xs text-text-tertiary">
        <FileText aria-hidden="true" className="h-3.5 w-3.5" />
        <span className="font-medium text-text-secondary">
          {result.source_type}
        </span>
        <span>·</span>
        <Calendar aria-hidden="true" className="h-3.5 w-3.5" />
        <span>{new Date(result.date).toLocaleDateString("de-DE")}</span>
        <span className="ml-auto rounded-md bg-indigo-50 px-1.5 py-0.5 text-xs font-semibold text-indigo-600">
          {Math.round(result.score * 100)}%
        </span>
      </div>
      <h3 className="mb-1 text-sm font-semibold text-text">
        {result.doc_title}
      </h3>
      <p className="text-sm text-text-secondary line-clamp-3">
        {result.content}
      </p>
      {result.entities.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {result.entities.map((e) => (
            <span
              key={e}
              className="rounded-full bg-surface-secondary px-2 py-0.5 text-xs text-text-secondary"
            >
              {e}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div role="status" className="flex items-center justify-center py-12">
          <Loader2
            aria-hidden="true"
            className="h-8 w-8 animate-spin text-text-tertiary"
          />
          <span className="sr-only">Wird geladen</span>
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}

function SearchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const initialQuery = searchParams.get("q") ?? "";
  const [query, setQuery] = useState(initialQuery);
  const [showFilters, setShowFilters] = useState(false);

  // Filters from URL
  const [sourceTypes, setSourceTypes] = useState<SourceType[]>(() => {
    const st = searchParams.get("source_types");
    return st ? (st.split(",") as SourceType[]) : [];
  });
  const [dateFrom, setDateFrom] = useState(searchParams.get("date_from") ?? "");
  const [dateTo, setDateTo] = useState(searchParams.get("date_to") ?? "");

  const filters: SearchFilters | undefined =
    sourceTypes.length > 0 || dateFrom || dateTo
      ? {
          source_types: sourceTypes.length > 0 ? sourceTypes : undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        }
      : undefined;

  const { data, isLoading, isFetching } = useSearch(query, filters);
  const saveMutation = useCreateSavedSearch();

  // Track search events (debounced via useSearch)
  const lastTrackedQuery = useRef("");
  useEffect(() => {
    if (data && query.length >= 2 && query !== lastTrackedQuery.current) {
      lastTrackedQuery.current = query;
      trackSearch("hybrid");
    }
  }, [data, query]);

  const syncUrl = useCallback(
    (q: string, st: SourceType[], df: string, dt: string) => {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (st.length > 0) params.set("source_types", st.join(","));
      if (df) params.set("date_from", df);
      if (dt) params.set("date_to", dt);
      const qs = params.toString();
      router.replace(`/search${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [router],
  );

  function handleQueryChange(value: string) {
    setQuery(value);
    syncUrl(value, sourceTypes, dateFrom, dateTo);
  }

  function toggleSourceType(st: SourceType) {
    const next = sourceTypes.includes(st)
      ? sourceTypes.filter((s) => s !== st)
      : [...sourceTypes, st];
    setSourceTypes(next);
    syncUrl(query, next, dateFrom, dateTo);
  }

  function clearFilters() {
    setSourceTypes([]);
    setDateFrom("");
    setDateTo("");
    syncUrl(query, [], "", "");
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-text">Suche</h1>

      {/* Search Input — Combobox with auto-complete, history, saved */}
      <div className="flex gap-2">
        <div className="flex-1">
          <SearchCombobox value={query} onChange={handleQueryChange} />
        </div>
        {query.length > 0 && (
          <button
            type="button"
            onClick={() => {
              const name = prompt("Name für gespeicherte Suche:");
              if (name) {
                saveMutation.mutate({ name, query, filters });
              }
            }}
            title="Suche speichern"
            className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
          >
            <Bookmark aria-hidden className="h-4 w-4" />
            <span className="hidden sm:inline">Speichern</span>
          </button>
        )}
      </div>
      {isFetching && (
        <div className="flex justify-end">
          <Loader2
            aria-hidden="true"
            className="h-5 w-5 animate-spin text-text-tertiary"
          />
        </div>
      )}

      {/* Filter Toggle */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setShowFilters(!showFilters)}
          aria-expanded={showFilters}
          className="inline-flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-sm text-text-secondary hover:bg-surface-secondary"
        >
          <Filter aria-hidden="true" className="h-4 w-4" />
          Filter
        </button>
        {filters && (
          <button
            onClick={clearFilters}
            className="inline-flex items-center gap-1 rounded-md text-sm text-text-tertiary hover:text-text-secondary"
          >
            <X aria-hidden="true" className="h-4 w-4" />
            Filter entfernen
          </button>
        )}
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <fieldset>
                <legend className="mb-2 text-sm font-medium text-text-secondary">
                  Quelltyp
                </legend>
                <div className="space-y-1">
                  {SOURCE_TYPE_OPTIONS.map((opt) => (
                    <label
                      key={opt.value}
                      className="flex items-center gap-2 text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={sourceTypes.includes(opt.value)}
                        onChange={() => toggleSourceType(opt.value)}
                        className="rounded border-border accent-indigo-600"
                      />
                      {opt.label}
                    </label>
                  ))}
                </div>
              </fieldset>
            </div>
            <div>
              <label
                htmlFor="filter-date-from"
                className="mb-2 block text-sm font-medium text-text-secondary"
              >
                Von
              </label>
              <input
                id="filter-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  syncUrl(query, sourceTypes, e.target.value, dateTo);
                }}
                className="w-full rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label
                htmlFor="filter-date-to"
                className="mb-2 block text-sm font-medium text-text-secondary"
              >
                Bis
              </label>
              <input
                id="filter-date-to"
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  syncUrl(query, sourceTypes, dateFrom, e.target.value);
                }}
                className="w-full rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
              />
            </div>
          </div>
        </div>
      )}

      {/* LLM-generated Answer */}
      {data?.answer && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4">
          <h2 className="mb-1 text-sm font-semibold text-indigo-800">
            KI-Zusammenfassung
          </h2>
          <p className="text-sm text-indigo-900">{data.answer}</p>
        </div>
      )}

      {/* Results */}
      {isLoading && query.length > 0 ? (
        <div role="status" className="flex items-center justify-center py-12">
          <Loader2
            aria-hidden="true"
            className="h-8 w-8 animate-spin text-text-tertiary"
          />
          <span className="sr-only">Wird geladen</span>
        </div>
      ) : data && data.results.length > 0 ? (
        <div className="space-y-3">
          <p className="text-sm text-text-tertiary">
            {data.results.length} Ergebnis
            {data.results.length !== 1 ? "se" : ""}
          </p>
          {data.results.map((result) => (
            <ResultCard key={result.chunk_id} result={result} />
          ))}
        </div>
      ) : query.length > 0 && !isLoading ? (
        <div className="rounded-xl border border-border bg-surface p-8 text-center">
          <SearchIcon
            aria-hidden="true"
            className="mx-auto mb-3 h-10 w-10 text-text-tertiary"
          />
          <h3 className="mb-1 text-sm font-semibold text-text">
            Keine Ergebnisse gefunden
          </h3>
          <p className="text-sm text-text-tertiary">
            Versuche andere Suchbegriffe oder entferne Filter.
          </p>
        </div>
      ) : null}
    </div>
  );
}
