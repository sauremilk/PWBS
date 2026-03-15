import { apiClient } from "@/lib/api-client";
import type {
  AutoCompleteResponse,
  SavedSearchCreate,
  SavedSearchItem,
  SearchHistoryResponse,
  SearchRequest,
  SearchResponse,
} from "@/types/api";

export async function search(data: SearchRequest): Promise<SearchResponse> {
  return apiClient.post<SearchResponse>("/search/", data);
}

export async function autocomplete(
  q: string,
  limit = 10,
): Promise<AutoCompleteResponse> {
  return apiClient.get<AutoCompleteResponse>(
    `/search/autocomplete?q=${encodeURIComponent(q)}&limit=${limit}`,
  );
}

export async function createSavedSearch(
  data: SavedSearchCreate,
): Promise<SavedSearchItem> {
  return apiClient.post<SavedSearchItem>("/search/saved", data);
}

export async function listSavedSearches(): Promise<SavedSearchItem[]> {
  return apiClient.get<SavedSearchItem[]>("/search/saved");
}

export async function deleteSavedSearch(id: string): Promise<void> {
  await apiClient.delete(`/search/saved/${id}`);
}

export async function getSearchHistory(): Promise<SearchHistoryResponse> {
  return apiClient.get<SearchHistoryResponse>("/search/history");
}
