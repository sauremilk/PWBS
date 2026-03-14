"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listBriefings, getBriefing, generateBriefing, submitFeedback } from "@/lib/api/briefings";
import type { BriefingType, FeedbackRequest } from "@/types/api";

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
    mutationFn: ({
      type,
      trigger_context,
    }: {
      type: BriefingType;
      trigger_context?: Record<string, unknown>;
    }) => generateBriefing({ briefing_type: type, trigger_context }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["briefings"] });
    },
  });
}

export function useBriefingFeedback(briefingId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: FeedbackRequest) => submitFeedback(briefingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["briefing", briefingId] });
    },
  });
}
