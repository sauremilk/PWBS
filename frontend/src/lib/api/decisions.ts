import { apiClient } from "@/lib/api-client";
import type {
  DecisionListResponse,
  DecisionDetailResponse,
  DecisionCreateRequest,
  DecisionUpdateRequest,
} from "@/types/api";

export async function listDecisions(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<DecisionListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const qs = query.toString();
  return apiClient.get<DecisionListResponse>(
    `/knowledge/decisions${qs ? `?${qs}` : ""}`,
  );
}

export async function getDecision(
  id: string,
): Promise<DecisionDetailResponse> {
  return apiClient.get<DecisionDetailResponse>(
    `/knowledge/decisions/${encodeURIComponent(id)}`,
  );
}

export async function createDecision(
  data: DecisionCreateRequest,
): Promise<DecisionDetailResponse> {
  return apiClient.post<DecisionDetailResponse>(
    "/knowledge/decisions",
    data,
  );
}

export async function updateDecision(
  id: string,
  data: DecisionUpdateRequest,
): Promise<DecisionDetailResponse> {
  return apiClient.patch<DecisionDetailResponse>(
    `/knowledge/decisions/${encodeURIComponent(id)}`,
    data,
  );
}

