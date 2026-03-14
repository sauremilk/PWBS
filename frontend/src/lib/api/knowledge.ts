import { apiClient } from "@/lib/api-client";
import type {
  EntityListResponse,
  EntityDetailResponse,
  EntityDocumentsResponse,
  GraphResponse,
  PatternListResponse,
} from "@/types/api";

export async function listEntities(
  params?: {
    type?: string;
    limit?: number;
    offset?: number;
  },
): Promise<EntityListResponse> {
  const query = new URLSearchParams();
  if (params?.type) query.set("type", params.type);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const qs = query.toString();
  return apiClient.get<EntityListResponse>(
    `/knowledge/entities${qs ? `?${qs}` : ""}`,
  );
}

export async function getEntity(id: string): Promise<EntityDetailResponse> {
  return apiClient.get<EntityDetailResponse>(
    `/knowledge/entities/${encodeURIComponent(id)}`,
  );
}

export async function getEntityDocuments(
  id: string,
): Promise<EntityDocumentsResponse> {
  return apiClient.get<EntityDocumentsResponse>(
    `/knowledge/entities/${encodeURIComponent(id)}/documents`,
  );
}

export async function getGraph(
  params?: { depth?: number; entity_id?: string },
): Promise<GraphResponse> {
  const query = new URLSearchParams();
  if (params?.depth) query.set("depth", String(params.depth));
  if (params?.entity_id) query.set("entity_id", params.entity_id);

  const qs = query.toString();
  return apiClient.get<GraphResponse>(
    `/knowledge/graph${qs ? `?${qs}` : ""}`,
  );
}

export async function getPatterns(
  params?: { pattern_type?: string; limit?: number },
): Promise<PatternListResponse> {
  const query = new URLSearchParams();
  if (params?.pattern_type) query.set("pattern_type", params.pattern_type);
  if (params?.limit) query.set("limit", String(params.limit));

  const qs = query.toString();
  return apiClient.get<PatternListResponse>(
    `/knowledge/patterns${qs ? `?${qs}` : ""}`,
  );
}
