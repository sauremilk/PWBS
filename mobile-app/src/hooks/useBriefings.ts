// Briefings hook with offline support (TASK-152)

import { useQuery } from "@tanstack/react-query";
import { fetchBriefing, fetchBriefings } from "../api/client";
import { cacheBriefings, getCachedBriefings } from "../storage/offline";
import type { Briefing } from "../types";

export function useBriefings() {
  return useQuery<Briefing[]>({
    queryKey: ["briefings"],
    queryFn: async () => {
      try {
        const data = await fetchBriefings(10);
        await cacheBriefings(data);
        return data;
      } catch {
        // Fallback to cached data when offline
        return getCachedBriefings();
      }
    },
    staleTime: 60_000,
  });
}

export function useBriefing(id: string) {
  return useQuery<Briefing>({
    queryKey: ["briefing", id],
    queryFn: () => fetchBriefing(id),
    enabled: !!id,
  });
}
