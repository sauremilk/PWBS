"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listConnectorTypes,
  getConnectionStatus,
  getAuthUrl,
  configure,
  disconnect,
  syncConnector,
  getConsentStatus,
  grantConsent,
  revokeConsent,
} from "@/lib/api/connectors";

export function useConnectorTypes() {
  return useQuery({
    queryKey: ["connectors", "types"],
    queryFn: listConnectorTypes,
  });
}

export function useConnectionStatus() {
  return useQuery({
    queryKey: ["connectors", "status"],
    queryFn: getConnectionStatus,
    refetchInterval: 15_000,
  });
}

export function useConnectOAuth() {
  return useMutation({
    mutationFn: async (connectorType: string) => {
      const { auth_url } = await getAuthUrl(connectorType);
      window.location.href = auth_url;
    },
  });
}

export function useConfigureConnector() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ type, vault_path }: { type: string; vault_path: string }) =>
      configure(type, { vault_path }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors"] });
    },
  });
}

export function useDisconnectConnector() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectorType: string) => disconnect(connectorType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors"] });
    },
  });
}

export function useSyncConnector() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectorType: string) => syncConnector(connectorType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors", "status"] });
    },
  });
}

export function useConsentStatus(connectorType: string | null) {
  return useQuery({
    queryKey: ["connectors", "consent", connectorType],
    queryFn: () => getConsentStatus(connectorType!),
    enabled: connectorType !== null,
  });
}

export function useGrantConsent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      connectorType,
      consentVersion,
    }: {
      connectorType: string;
      consentVersion: number;
    }) => grantConsent(connectorType, { consent_version: consentVersion }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors"] });
    },
  });
}

export function useRevokeConsent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectorType: string) => revokeConsent(connectorType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors"] });
    },
  });
}
