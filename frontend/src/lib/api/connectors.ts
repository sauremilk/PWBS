import { apiClient } from "@/lib/api-client";
import type {
  ConnectorListResponse,
  ConnectionStatusResponse,
  AuthUrlResponse,
  CallbackRequest,
  CallbackResponse,
  ConfigRequest,
  ConfigResponse,
  DisconnectResponse,
  SyncResponse,
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
