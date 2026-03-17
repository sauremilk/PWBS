"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listBriefings,
  getBriefing,
  generateBriefing,
  submitFeedback,
} from "@/lib/api/briefings";
import {
  getBriefingPreferences,
  updateBriefingPreferences,
} from "@/lib/api/user";
import { DEMO_BRIEFING, DEMO_BRIEFING_TIMEOUT_MS } from "@/lib/demo-briefing";
import type {
  BriefingType,
  FeedbackRequest,
  BriefingPreferencesUpdate,
  BriefingDetailResponse,
} from "@/types/api";

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

/**
 * Hook der ein echtes Briefing generiert, aber bei Timeout (>2 min)
 * oder LLM-Fehler automatisch das Demo-Briefing als Fallback liefert.
 * Sobald das echte Briefing verfügbar wird, ersetzt es den Fallback.
 */
export function useGenerateBriefingWithFallback() {
  const generate = useGenerateBriefing();
  const [demoBriefing, setDemoBriefing] =
    useState<BriefingDetailResponse | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  function startGeneration(type: BriefingType) {
    setDemoBriefing(null);

    // Starte Timer: nach DEMO_BRIEFING_TIMEOUT_MS das Demo-Briefing zeigen
    timerRef.current = setTimeout(() => {
      if (generate.isPending) {
        setDemoBriefing(DEMO_BRIEFING);
      }
    }, DEMO_BRIEFING_TIMEOUT_MS);

    generate.mutate(
      { type },
      {
        onSuccess: () => {
          if (timerRef.current) clearTimeout(timerRef.current);
          setDemoBriefing(null);
        },
        onError: () => {
          if (timerRef.current) clearTimeout(timerRef.current);
          setDemoBriefing(DEMO_BRIEFING);
        },
      },
    );
  }

  return {
    startGeneration,
    isPending: generate.isPending,
    isError: generate.isError,
    demoBriefing,
    isShowingDemo: demoBriefing !== null,
  };
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

export function useBriefingPreferences() {
  return useQuery({
    queryKey: ["briefing-preferences"],
    queryFn: getBriefingPreferences,
  });
}

export function useUpdateBriefingPreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BriefingPreferencesUpdate) =>
      updateBriefingPreferences(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["briefing-preferences"] });
    },
  });
}
