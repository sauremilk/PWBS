"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSettings,
  updateSettings,
  startExport,
  getExportStatus,
  requestAccountDeletion,
  cancelAccountDeletion,
  getDataReport,
  getLlmUsage,
} from "@/lib/api/user";
import type { UserSettingsUpdate, AccountDeletionRequest } from "@/types/api";

export function useUserSettings() {
  return useQuery({
    queryKey: ["user", "settings"],
    queryFn: getSettings,
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UserSettingsUpdate) => updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user", "settings"] });
    },
  });
}

export function useStartExport() {
  return useMutation({
    mutationFn: () => startExport(),
  });
}

export function useExportStatus(exportId: string | null) {
  return useQuery({
    queryKey: ["user", "export", exportId],
    queryFn: () => getExportStatus(exportId!),
    enabled: !!exportId,
    refetchInterval: (query) =>
      query.state.data?.status === "completed" ? false : 5_000,
  });
}

export function useRequestDeletion() {
  return useMutation({
    mutationFn: (data: AccountDeletionRequest) => requestAccountDeletion(data),
  });
}

export function useCancelDeletion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => cancelAccountDeletion(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user"] });
    },
  });
}

export function useDataReport() {
  return useQuery({
    queryKey: ["user", "data-report"],
    queryFn: getDataReport,
  });
}

export function useLlmUsage(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["user", "llm-usage", params],
    queryFn: () => getLlmUsage(params),
  });
}
