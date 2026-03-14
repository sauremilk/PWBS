import { apiClient } from "@/lib/api-client";
import type { SearchRequest, SearchResponse } from "@/types/api";

export async function search(data: SearchRequest): Promise<SearchResponse> {
  return apiClient.post<SearchResponse>("/search/", data);
}
