"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listPlugins,
  getPlugin,
  installPlugin,
  uninstallPlugin,
  listInstalled,
  ratePlugin,
  getPluginRatings,
} from "@/lib/api/marketplace";
import type { RatePluginRequest } from "@/types/marketplace";

export function usePlugins(params: {
  plugin_type?: string;
  search?: string;
  offset?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["marketplace", "plugins", params],
    queryFn: () => listPlugins(params),
  });
}

export function usePlugin(pluginId: string) {
  return useQuery({
    queryKey: ["marketplace", "plugin", pluginId],
    queryFn: () => getPlugin(pluginId),
    enabled: !!pluginId,
  });
}

export function useInstalledPlugins() {
  return useQuery({
    queryKey: ["marketplace", "installed"],
    queryFn: listInstalled,
  });
}

export function useInstallPlugin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      pluginId,
      config,
    }: {
      pluginId: string;
      config?: Record<string, unknown>;
    }) => installPlugin(pluginId, { config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketplace"] });
    },
  });
}

export function useUninstallPlugin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (pluginId: string) => uninstallPlugin(pluginId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketplace"] });
    },
  });
}

export function useRatePlugin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      pluginId,
      ...body
    }: { pluginId: string } & RatePluginRequest) => ratePlugin(pluginId, body),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: ["marketplace", "plugin", vars.pluginId],
      });
      queryClient.invalidateQueries({
        queryKey: ["marketplace", "ratings", vars.pluginId],
      });
    },
  });
}

export function usePluginRatings(
  pluginId: string,
  params: { offset?: number; limit?: number } = {},
) {
  return useQuery({
    queryKey: ["marketplace", "ratings", pluginId, params],
    queryFn: () => getPluginRatings(pluginId, params),
    enabled: !!pluginId,
  });
}
