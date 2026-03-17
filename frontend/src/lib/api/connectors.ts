import { apiClient } from "@/lib/api-client";
import type {
  ConnectorListResponse,
  ConnectionStatusResponse,
  AuthUrlResponse,
  CallbackRequest,
  CallbackResponse,
  ConfigRequest,
  ConfigResponse,
  ConsentGrantRequest,
  ConsentRevokeResponse,
  ConsentStatusResponse,
  DisconnectResponse,
  SyncHistoryResponse,
  SyncResponse,
  UploadResponse,
} from "@/types/api";

export async function listConnectorTypes(): Promise<ConnectorListResponse> {
  return apiClient.get<ConnectorListResponse>("/connectors/types");
}

export async function getConnectionStatus(): Promise<ConnectionStatusResponse> {
  return apiClient.get<ConnectionStatusResponse>("/connectors/status");
}

export async function getAuthUrl(
  connectorType: string,
): Promise<AuthUrlResponse> {
  return apiClient.get<AuthUrlResponse>(
    `/connectors/${encodeURIComponent(connectorType)}/auth`,
  );
}

export async function handleCallback(
  connectorType: string,
  data: CallbackRequest,
): Promise<CallbackResponse> {
  return apiClient.post<CallbackResponse>(
    `/connectors/${encodeURIComponent(connectorType)}/callback`,
    data,
  );
}

export async function configure(
  connectorType: string,
  data: ConfigRequest,
): Promise<ConfigResponse> {
  return apiClient.post<ConfigResponse>(
    `/connectors/${encodeURIComponent(connectorType)}/config`,
    data,
  );
}

export async function disconnect(
  connectorType: string,
): Promise<DisconnectResponse> {
  return apiClient.delete<DisconnectResponse>(
    `/connectors/${encodeURIComponent(connectorType)}`,
  );
}

export async function syncConnector(
  connectorType: string,
): Promise<SyncResponse> {
  return apiClient.post<SyncResponse>(
    `/connectors/${encodeURIComponent(connectorType)}/sync`,
  );
}

export async function getConsentStatus(
  connectorType: string,
): Promise<ConsentStatusResponse> {
  return apiClient.get<ConsentStatusResponse>(
    `/connectors/${encodeURIComponent(connectorType)}/consent`,
  );
}

export async function grantConsent(
  connectorType: string,
  data: ConsentGrantRequest,
): Promise<ConsentStatusResponse> {
  return apiClient.post<ConsentStatusResponse>(
    `/connectors/${encodeURIComponent(connectorType)}/consent`,
    data,
  );
}

export async function revokeConsent(
  connectorType: string,
): Promise<ConsentRevokeResponse> {
  return apiClient.delete<ConsentRevokeResponse>(
    `/connectors/${encodeURIComponent(connectorType)}/consent`,
  );
}

export async function getSyncHistory(
  connectorType: string,
  offset: number = 0,
  limit: number = 10,
): Promise<SyncHistoryResponse> {
  return apiClient.get<SyncHistoryResponse>(
    `/connectors/${encodeURIComponent(connectorType)}/history?offset=${offset}&limit=${limit}`,
  );
}

/** Upload an Obsidian vault ZIP or single .md file (ADR-018). */
export async function uploadObsidian(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm<UploadResponse>(
    "/connectors/obsidian/upload",
    formData,
  );
}
