import { apiClient } from "@/lib/api-client";
import type {
  DocumentListResponse,
  DocumentDetailResponse,
} from "@/types/api";

export async function listDocuments(
  params?: {
    source_type?: string;
    limit?: number;
    offset?: number;
  },
): Promise<DocumentListResponse> {
  const query = new URLSearchParams();
  if (params?.source_type) query.set("source_type", params.source_type);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const qs = query.toString();
  return apiClient.get<DocumentListResponse>(
    `/documents${qs ? `?${qs}` : ""}`,
  );
}

export async function getDocument(
  id: string,
): Promise<DocumentDetailResponse> {
  return apiClient.get<DocumentDetailResponse>(
    `/documents/${encodeURIComponent(id)}`,
  );
}
