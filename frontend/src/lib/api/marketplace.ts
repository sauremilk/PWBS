import { apiClient } from "@/lib/api-client";
import type {
  PluginListResponse,
  PluginDetail,
  InstalledPlugin,
  InstallPluginRequest,
  RatePluginRequest,
  PluginRating,
  PluginRatingListResponse,
} from "@/types/marketplace";

export async function listPlugins(params: {
  plugin_type?: string;
  search?: string;
  offset?: number;
  limit?: number;
}): Promise<PluginListResponse> {
  const query = new URLSearchParams();
  if (params.plugin_type) query.set("plugin_type", params.plugin_type);
  if (params.search) query.set("search", params.search);
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  const qs = query.toString();
  return apiClient.get<PluginListResponse>(
    `/marketplace/plugins${qs ? `?${qs}` : ""}`,
  );
}

export async function getPlugin(pluginId: string): Promise<PluginDetail> {
  return apiClient.get<PluginDetail>(
    `/marketplace/plugins/${encodeURIComponent(pluginId)}`,
  );
}

export async function installPlugin(
  pluginId: string,
  body: InstallPluginRequest = {},
): Promise<InstalledPlugin> {
  return apiClient.post<InstalledPlugin>(
    `/marketplace/plugins/${encodeURIComponent(pluginId)}/install`,
    body,
  );
}

export async function uninstallPlugin(pluginId: string): Promise<void> {
  return apiClient.delete<void>(
    `/marketplace/plugins/${encodeURIComponent(pluginId)}/uninstall`,
  );
}

export async function listInstalled(): Promise<InstalledPlugin[]> {
  return apiClient.get<InstalledPlugin[]>("/marketplace/installed");
}

export async function ratePlugin(
  pluginId: string,
  body: RatePluginRequest,
): Promise<PluginRating> {
  return apiClient.post<PluginRating>(
    `/marketplace/plugins/${encodeURIComponent(pluginId)}/rate`,
    body,
  );
}

export async function getPluginRatings(
  pluginId: string,
  params: { offset?: number; limit?: number } = {},
): Promise<PluginRatingListResponse> {
  const query = new URLSearchParams();
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  const qs = query.toString();
  return apiClient.get<PluginRatingListResponse>(
    `/marketplace/plugins/${encodeURIComponent(pluginId)}/ratings${qs ? `?${qs}` : ""}`,
  );
}
