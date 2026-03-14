import { apiClient } from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CreateOrgRequest {
  name: string;
  description?: string;
}

export interface OrgResponse {
  id: string;
  name: string;
  slug: string;
  description: string;
  created_at: string;
}

export interface OrgListResponse {
  items: OrgResponse[];
  count: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function listOrganizations(): Promise<OrgListResponse> {
  return apiClient.get<OrgListResponse>("/organizations");
}

export async function createOrganization(
  data: CreateOrgRequest,
): Promise<OrgResponse> {
  return apiClient.post<OrgResponse>("/organizations", data);
}

export async function getOrganization(orgId: string): Promise<OrgResponse> {
  return apiClient.get<OrgResponse>(
    `/organizations/${encodeURIComponent(orgId)}`,
  );
}
