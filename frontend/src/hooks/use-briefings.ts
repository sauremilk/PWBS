"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listBriefings, getBriefing, generateBriefing } from "@/lib/api/briefings";
import type { BriefingType } from "@/types/api";

export function useBriefingList(params?: { type?: string; limit?: number }) {
  return useQuery({
    queryKey: ["briefings", params],
    queryFn: () => listBriefings(params),
  });
}

export function useLatestBriefing(type: BriefingType) {
  return useQuery({
    queryKey: ["briefings", "latest", type],
    queryFn: () => listBriefings({ type, limit: 1 }),
    select: (data) => data.briefings[0] ?? null,
  });
}

export function useBriefingDetail(id: string) {
  return useQuery({
    queryKey: ["briefing", id],
    queryFn: () => getBriefing(id),
    enabled: !!id,
  });
}

export function useGenerateBriefing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (type: BriefingType) =>
      generateBriefing({ briefing_type: type }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["briefings"] });
    },
  });
}
