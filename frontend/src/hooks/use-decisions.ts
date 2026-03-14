"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as decisionsApi from "@/lib/api/decisions";
import type {
  DecisionListResponse,
  DecisionDetailResponse,
  DecisionCreateRequest,
  DecisionUpdateRequest,
} from "@/types/api";

export function useDecisions(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery<DecisionListResponse>({
    queryKey: ["decisions", params],
    queryFn: () => decisionsApi.listDecisions(params),
  });
}

export function useDecisionDetail(id: string | null) {
  return useQuery<DecisionDetailResponse>({
    queryKey: ["decision", id],
    queryFn: () => decisionsApi.getDecision(id!),
    enabled: !!id,
  });
}

export function useCreateDecision() {
  const queryClient = useQueryClient();
  return useMutation<DecisionDetailResponse, Error, DecisionCreateRequest>({
    mutationFn: (data) => decisionsApi.createDecision(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["decisions"] });
    },
  });
}

export function useUpdateDecision(id: string) {
  const queryClient = useQueryClient();
  return useMutation<DecisionDetailResponse, Error, DecisionUpdateRequest>({
    mutationFn: (data) => decisionsApi.updateDecision(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["decisions"] });
      queryClient.invalidateQueries({ queryKey: ["decision", id] });
    },
  });
}

