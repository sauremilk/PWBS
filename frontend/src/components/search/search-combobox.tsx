"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Search as SearchIcon, Clock, Bookmark, X } from "lucide-react";
import {
  useAutoComplete,
  useSearchHistory,
  useSavedSearches,
  useDeleteSavedSearch,
} from "@/hooks/use-search";
import type {
  AutoCompleteItem,
  SavedSearchItem,
  SearchHistoryItem,
} from "@/types/api";

interface SearchComboboxProps {
  value: string;
  onChange: (value: string) => void;
  onSuggestionSelect?: (item: AutoCompleteItem) => void;
  placeholder?: string;
}

export function SearchCombobox({
  value,
  onChange,
  onSuggestionSelect,
  placeholder = "Dokumente, Personen, Projekte durchsuchen…",
}: SearchComboboxProps) {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<
    "suggestions" | "history" | "saved"
  >("suggestions");
  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: acData } = useAutoComplete(value);
  const { data: historyData } = useSearchHistory();
  const { data: savedData } = useSavedSearches();
  const deleteSaved = useDeleteSavedSearch();

  const suggestions = acData?.suggestions ?? [];
  const historyItems = historyData?.items ?? [];
  const savedItems = savedData ?? [];

  const hasContent =
    (activeTab === "suggestions" && suggestions.length > 0) ||
    (activeTab === "history" && historyItems.length > 0) ||
    (activeTab === "saved" && savedItems.length > 0);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(e.target.value);
      setActiveTab("suggestions");
      setOpen(true);
    },
    [onChange],
  );

  function selectSuggestion(item: AutoCompleteItem) {
    onChange(item.name);
    setOpen(false);
    onSuggestionSelect?.(item);
  }

  function selectHistory(item: SearchHistoryItem) {
    onChange(item.query);
    setOpen(false);
  }

  function selectSaved(item: SavedSearchItem) {
    onChange(item.query);
    setOpen(false);
  }

  return (
    <div ref={wrapperRef} className="relative">
      <SearchIcon
        aria-hidden="true"
        className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-text-tertiary"
      />
      <input
        ref={inputRef}
        type="text"
        role="combobox"
        aria-expanded={open && hasContent ? "true" : "false"}
        aria-controls="search-listbox"
        aria-haspopup="listbox"
        aria-label="Suchfeld"
        value={value}
        onChange={handleInputChange}
        onFocus={() => setOpen(true)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-border bg-surface py-3 pl-10 pr-4 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      />

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-xl border border-border bg-surface shadow-lg">
          {/* Tabs */}
          <div className="flex border-b border-border/50">
            <button
              type="button"
              onClick={() => setActiveTab("suggestions")}
              className={`flex-1 px-3 py-2 text-xs font-medium ${
                activeTab === "suggestions"
                  ? "border-b-2 border-indigo-500 text-indigo-600"
                  : "text-text-tertiary hover:text-text-secondary"
              }`}
            >
              <SearchIcon aria-hidden className="mr-1 inline h-3 w-3" />
              Vorschläge
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("history")}
              className={`flex-1 px-3 py-2 text-xs font-medium ${
                activeTab === "history"
                  ? "border-b-2 border-indigo-500 text-indigo-600"
                  : "text-text-tertiary hover:text-text-secondary"
              }`}
            >
              <Clock aria-hidden className="mr-1 inline h-3 w-3" />
              Verlauf
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("saved")}
              className={`flex-1 px-3 py-2 text-xs font-medium ${
                activeTab === "saved"
                  ? "border-b-2 border-indigo-500 text-indigo-600"
                  : "text-text-tertiary hover:text-text-secondary"
              }`}
            >
              <Bookmark aria-hidden className="mr-1 inline h-3 w-3" />
              Gespeichert
            </button>
          </div>

          {/* Suggestions panel */}
          {activeTab === "suggestions" && suggestions.length > 0 && (
            <ul
              id="search-listbox"
              role="listbox"
              aria-label="Suchvorschläge"
              className="max-h-60 overflow-y-auto py-1"
            >
              {suggestions.map((item) => (
                <li
                  key={item.entity_id}
                  role="option"
                  aria-selected="false"
                  tabIndex={0}
                  onClick={() => selectSuggestion(item)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") selectSuggestion(item);
                  }}
                  className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm hover:bg-surface-secondary"
                >
                  <span className="rounded bg-surface-secondary px-1.5 py-0.5 text-xs text-text-tertiary">
                    {item.entity_type}
                  </span>
                  <span className="text-text">{item.name}</span>
                </li>
              ))}
            </ul>
          )}

          {/* History panel */}
          {activeTab === "history" && historyItems.length > 0 && (
            <div role="menu" className="max-h-60 overflow-y-auto py-1">
              {historyItems.slice(0, 10).map((item) => (
                <div
                  key={item.id}
                  role="menuitem"
                  tabIndex={0}
                  onClick={() => selectHistory(item)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") selectHistory(item);
                  }}
                  className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm hover:bg-surface-secondary"
                >
                  <Clock
                    aria-hidden
                    className="h-3.5 w-3.5 text-text-tertiary"
                  />
                  <span className="flex-1 text-text">{item.query}</span>
                  <span className="text-xs text-text-tertiary">
                    {item.result_count} Ergebnis
                    {item.result_count !== 1 ? "se" : ""}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Saved searches panel */}
          {activeTab === "saved" && savedItems.length > 0 && (
            <ul className="max-h-60 overflow-y-auto py-1">
              {savedItems.map((item) => (
                <li
                  key={item.id}
                  className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm hover:bg-surface-secondary"
                >
                  <Bookmark
                    aria-hidden
                    className="h-3.5 w-3.5 text-text-tertiary"
                  />
                  <button
                    type="button"
                    onClick={() => selectSaved(item)}
                    className="flex flex-1 flex-col text-left"
                  >
                    <span className="font-medium text-text">{item.name}</span>
                    <span className="text-xs text-text-tertiary">
                      {item.query}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSaved.mutate(item.id);
                    }}
                    aria-label={`Gespeicherte Suche "${item.name}" löschen`}
                    className="rounded p-1 text-text-tertiary hover:bg-surface-secondary hover:text-text-secondary"
                  >
                    <X aria-hidden className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Empty state */}
          {!hasContent && (
            <p className="px-3 py-4 text-center text-sm text-text-tertiary">
              {activeTab === "suggestions" &&
                value.length < 2 &&
                "Mindestens 2 Zeichen eingeben…"}
              {activeTab === "suggestions" &&
                value.length >= 2 &&
                "Keine Vorschläge"}
              {activeTab === "history" && "Noch kein Suchverlauf"}
              {activeTab === "saved" && "Noch keine gespeicherten Suchen"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
