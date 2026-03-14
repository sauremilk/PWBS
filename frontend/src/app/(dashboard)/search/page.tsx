"use client";

import { Suspense, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search as SearchIcon, Filter, X, FileText, Calendar, Loader2 } from "lucide-react";
import { useSearch } from "@/hooks/use-search";
import type { SearchFilters, SourceType, SearchResult } from "@/types/api";

const SOURCE_TYPE_OPTIONS: { value: SourceType; label: string }[] = [
  { value: "google_calendar", label: "Google Calendar" },
  { value: "google_drive", label: "Google Drive" },
  { value: "gmail", label: "Gmail" },
  { value: "notion", label: "Notion" },
  { value: "obsidian", label: "Obsidian" },
  { value: "zoom_transcript", label: "Zoom" },
  { value: "slack", label: "Slack" },
];

function ResultCard({ result }: { result: SearchResult }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-sm">
      <div className="mb-2 flex items-center gap-2 text-xs text-gray-500">
        <FileText className="h-3.5 w-3.5" />
        <span className="font-medium">{result.source_type}</span>
        <span>·</span>
        <Calendar className="h-3.5 w-3.5" />
        <span>{new Date(result.date).toLocaleDateString("de-DE")}</span>
        <span className="ml-auto rounded bg-blue-50 px-1.5 py-0.5 text-xs font-medium text-blue-700">
          {Math.round(result.score * 100)}%
        </span>
      </div>
      <h3 className="mb-1 text-sm font-semibold text-gray-900">{result.doc_title}</h3>
      <p className="text-sm text-gray-600 line-clamp-3">{result.content}</p>
      {result.entities.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {result.entities.map((e) => (
            <span key={e} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
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
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
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
      <h1 className="text-2xl font-bold text-gray-900">Suche</h1>

      {/* Search Input */}
      <div className="relative">
        <SearchIcon className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          placeholder="Dokumente, Personen, Projekte durchsuchen…"
          className="w-full rounded-lg border border-gray-300 py-3 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          autoFocus
        />
        {isFetching && (
          <Loader2 className="absolute right-3 top-1/2 h-5 w-5 -translate-y-1/2 animate-spin text-gray-400" />
        )}
      </div>

      {/* Filter Toggle */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
        >
          <Filter className="h-4 w-4" />
          Filter
        </button>
        {filters && (
          <button
            onClick={clearFilters}
            className="inline-flex items-center gap-1 rounded-md text-sm text-gray-500 hover:text-gray-700"
          >
            <X className="h-4 w-4" />
            Filter entfernen
          </button>
        )}
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Quelltyp</label>
              <div className="space-y-1">
                {SOURCE_TYPE_OPTIONS.map((opt) => (
                  <label key={opt.value} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={sourceTypes.includes(opt.value)}
                      onChange={() => toggleSourceType(opt.value)}
                      className="rounded border-gray-300"
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label htmlFor="filter-date-from" className="mb-2 block text-sm font-medium text-gray-700">Von</label>
              <input
                id="filter-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  syncUrl(query, sourceTypes, e.target.value, dateTo);
                }}
                className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="filter-date-to" className="mb-2 block text-sm font-medium text-gray-700">Bis</label>
              <input
                id="filter-date-to"
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  syncUrl(query, sourceTypes, dateFrom, e.target.value);
                }}
                className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
          </div>
        </div>
      )}

      {/* LLM-generated Answer */}
      {data?.answer && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <h2 className="mb-1 text-sm font-semibold text-blue-800">KI-Zusammenfassung</h2>
          <p className="text-sm text-blue-900">{data.answer}</p>
        </div>
      )}

      {/* Results */}
      {isLoading && query.length > 0 ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : data && data.results.length > 0 ? (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">
            {data.results.length} Ergebnis{data.results.length !== 1 ? "se" : ""}
          </p>
          {data.results.map((result) => (
            <ResultCard key={result.chunk_id} result={result} />
          ))}
        </div>
      ) : query.length > 0 && !isLoading ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
          <SearchIcon className="mx-auto mb-3 h-10 w-10 text-gray-300" />
          <h3 className="mb-1 text-sm font-semibold text-gray-900">Keine Ergebnisse gefunden</h3>
          <p className="text-sm text-gray-500">
            Versuche andere Suchbegriffe oder entferne Filter.
          </p>
        </div>
      ) : null}
    </div>
  );
}
