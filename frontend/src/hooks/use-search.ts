"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { search } from "@/lib/api/search";
import type { SearchFilters } from "@/types/api";

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
    queryFn: () =>
      search({ query: debouncedQuery, filters, limit }),
    enabled: debouncedQuery.length > 0,
  });
}
