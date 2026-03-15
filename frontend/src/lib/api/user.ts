import { apiClient } from "@/lib/api-client";
import type {
  UserSettingsResponse,
  UserSettingsUpdate,
  ExportStartResponse,
  ExportStatusResponse,
  AccountDeletionRequest,
  AccountDeletionResponse,
  CancelDeletionResponse,
  AuditLogResponse,
  SecurityStatusResponse,
  DataReportResponse,
  LlmUsageResponse,
  BriefingPreferencesResponse,
  BriefingPreferencesUpdate,
} from "@/types/api";

export async function getSettings(): Promise<UserSettingsResponse> {
  return apiClient.get<UserSettingsResponse>("/user/settings");
}

export async function updateSettings(
  data: UserSettingsUpdate,
): Promise<UserSettingsResponse> {
  return apiClient.patch<UserSettingsResponse>("/user/settings", data);
}

export async function startExport(): Promise<ExportStartResponse> {
  return apiClient.post<ExportStartResponse>("/user/export");
}

export async function getExportStatus(
  exportId: string,
): Promise<ExportStatusResponse> {
  return apiClient.get<ExportStatusResponse>(
    `/user/export/${encodeURIComponent(exportId)}`,
  );
}

export async function requestAccountDeletion(
  data: AccountDeletionRequest,
): Promise<AccountDeletionResponse> {
  return apiClient.post<AccountDeletionResponse>("/user/delete", data);
}

export async function cancelAccountDeletion(): Promise<CancelDeletionResponse> {
  return apiClient.post<CancelDeletionResponse>("/user/delete/cancel");
}

export async function getAuditLog(params?: {
  limit?: number;
  offset?: number;
}): Promise<AuditLogResponse> {
  const query = new URLSearchParams();
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const qs = query.toString();
  return apiClient.get<AuditLogResponse>(
    `/user/audit-log${qs ? `?${qs}` : ""}`,
  );
}

export async function getSecurityStatus(): Promise<SecurityStatusResponse> {
  return apiClient.get<SecurityStatusResponse>("/user/security-status");
}

export async function getDataReport(): Promise<DataReportResponse> {
  return apiClient.get<DataReportResponse>("/user/data-report");
}

export async function getLlmUsage(params?: {
  limit?: number;
  offset?: number;
}): Promise<LlmUsageResponse> {
  const query = new URLSearchParams();
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const qs = query.toString();
  return apiClient.get<LlmUsageResponse>(
    `/user/llm-usage${qs ? `?${qs}` : ""}`,
  );
}

export async function getBriefingPreferences(): Promise<BriefingPreferencesResponse> {
  return apiClient.get<BriefingPreferencesResponse>("/user/briefing-preferences");
}

export async function updateBriefingPreferences(
  data: BriefingPreferencesUpdate,
): Promise<BriefingPreferencesResponse> {
  return apiClient.patch<BriefingPreferencesResponse>(
    "/user/briefing-preferences",
    data,
  );
}
