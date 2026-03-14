// Search hook (TASK-152)

import { useQuery } from "@tanstack/react-query";
import { search as apiSearch } from "../api/client";
import type { SearchResult } from "../types";

export function useSearch(query: string) {
  return useQuery<SearchResult[]>({
    queryKey: ["search", query],
    queryFn: () => apiSearch(query),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });
}
