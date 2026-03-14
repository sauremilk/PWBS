import { apiClient } from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Types (mirror backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface OrgDashboardResponse {
  org_id: string;
  org_name: string;
  member_count: number;
  connector_count: number;
  shared_connector_count: number;
  document_count: number;
}

export interface MemberDetail {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  joined_at: string;
}

export interface MemberListResponse {
  members: MemberDetail[];
  count: number;
}

export interface InviteRequest {
  email: string;
  role?: "owner" | "member" | "viewer";
}

export interface InviteResponse {
  user_id: string;
  email: string;
  role: string;
  org_id: string;
}

export interface OrgConnector {
  id: string;
  source_type: string;
  status: string;
  owner_email: string;
  organization_id: string | null;
  created_at: string;
}

export interface OrgConnectorListResponse {
  connectors: OrgConnector[];
  count: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getDashboard(
  orgId: string,
): Promise<OrgDashboardResponse> {
  return apiClient.get<OrgDashboardResponse>(
    `/admin/org/${encodeURIComponent(orgId)}/dashboard`,
  );
}

export async function listMembers(orgId: string): Promise<MemberListResponse> {
  return apiClient.get<MemberListResponse>(
    `/admin/org/${encodeURIComponent(orgId)}/members`,
  );
}

export async function inviteMember(
  orgId: string,
  data: InviteRequest,
): Promise<InviteResponse> {
  return apiClient.post<InviteResponse>(
    `/admin/org/${encodeURIComponent(orgId)}/invite`,
    data,
  );
}

export async function listOrgConnectors(
  orgId: string,
): Promise<OrgConnectorListResponse> {
  return apiClient.get<OrgConnectorListResponse>(
    `/admin/org/${encodeURIComponent(orgId)}/connectors`,
  );
}

export async function shareConnector(
  orgId: string,
  connectorId: string,
): Promise<OrgConnector> {
  return apiClient.post<OrgConnector>(
    `/admin/org/${encodeURIComponent(orgId)}/connectors/${encodeURIComponent(connectorId)}/share`,
  );
}

export async function unshareConnector(
  orgId: string,
  connectorId: string,
): Promise<void> {
  return apiClient.delete<void>(
    `/admin/org/${encodeURIComponent(orgId)}/connectors/${encodeURIComponent(connectorId)}/share`,
  );
}
