"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  autocomplete,
  createSavedSearch,
  deleteSavedSearch,
  getSearchHistory,
  listSavedSearches,
  search,
} from "@/lib/api/search";
import type { SavedSearchCreate, SearchFilters } from "@/types/api";

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

export function useSearch(query: string, filters?: SearchFilters, limit = 10) {
  const debouncedQuery = useDebounce(query, 300);

  return useQuery({
    queryKey: ["search", debouncedQuery, filters, limit],
    queryFn: () => search({ query: debouncedQuery, filters, limit }),
    enabled: debouncedQuery.length > 0,
  });
}

export function useAutoComplete(query: string) {
  const debouncedQuery = useDebounce(query, 200);

  return useQuery({
    queryKey: ["autocomplete", debouncedQuery],
    queryFn: () => autocomplete(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  });
}

export function useSavedSearches() {
  return useQuery({
    queryKey: ["savedSearches"],
    queryFn: listSavedSearches,
  });
}

export function useCreateSavedSearch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SavedSearchCreate) => createSavedSearch(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["savedSearches"] });
    },
  });
}

export function useDeleteSavedSearch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteSavedSearch(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["savedSearches"] });
    },
  });
}

export function useSearchHistory() {
  return useQuery({
    queryKey: ["searchHistory"],
    queryFn: getSearchHistory,
  });
}
