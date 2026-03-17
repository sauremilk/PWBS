/**
 * TypeScript types for the PWBS Marketplace API (TASK-165).
 */

export type PluginType =
  | "connector"
  | "briefing_template"
  | "processing"
  | "agent";

export type SortField = "popularity" | "date" | "rating";

export interface PluginSummary {
  id: string;
  slug: string;
  version: string;
  name: string;
  description: string;
  plugin_type: string;
  is_verified: boolean;
  install_count: number;
  icon_url: string | null;
  published_at: string | null;
}

export interface PluginDetail extends PluginSummary {
  manifest: Record<string, unknown>;
  permissions: string[];
  entry_point: string;
  repository_url: string | null;
  rating_sum: number;
  rating_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface PluginListResponse {
  plugins: PluginSummary[];
  total: number;
  offset: number;
  limit: number;
}

export interface InstalledPlugin {
  id: string;
  plugin_id: string;
  config: Record<string, unknown>;
  is_enabled: boolean;
  installed_at: string;
  plugin: PluginSummary;
}

export interface PluginRating {
  id: string;
  user_id: string;
  plugin_id: string;
  score: number;
  review_text: string | null;
  rated_at: string;
}

export interface PluginRatingListResponse {
  ratings: PluginRating[];
  total: number;
  offset: number;
  limit: number;
}

export interface InstallPluginRequest {
  config?: Record<string, unknown>;
}

export interface RatePluginRequest {
  score: number;
  review_text?: string | null;
}
