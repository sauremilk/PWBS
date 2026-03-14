"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getDashboard,
  listMembers,
  inviteMember,
  listOrgConnectors,
  shareConnector,
  unshareConnector,
} from "@/lib/api/admin";
import type { InviteRequest } from "@/lib/api/admin";

export function useOrgDashboard(orgId: string | null) {
  return useQuery({
    queryKey: ["admin", "dashboard", orgId],
    queryFn: () => getDashboard(orgId!),
    enabled: !!orgId,
  });
}

export function useOrgMembers(orgId: string | null) {
  return useQuery({
    queryKey: ["admin", "members", orgId],
    queryFn: () => listMembers(orgId!),
    enabled: !!orgId,
  });
}

export function useInviteMember(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InviteRequest) => inviteMember(orgId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "members", orgId] });
      queryClient.invalidateQueries({
        queryKey: ["admin", "dashboard", orgId],
      });
    },
  });
}

export function useOrgConnectors(orgId: string | null) {
  return useQuery({
    queryKey: ["admin", "connectors", orgId],
    queryFn: () => listOrgConnectors(orgId!),
    enabled: !!orgId,
  });
}

export function useShareConnector(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectorId: string) => shareConnector(orgId, connectorId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin", "connectors", orgId],
      });
      queryClient.invalidateQueries({
        queryKey: ["admin", "dashboard", orgId],
      });
    },
  });
}

export function useUnshareConnector(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectorId: string) => unshareConnector(orgId, connectorId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin", "connectors", orgId],
      });
      queryClient.invalidateQueries({
        queryKey: ["admin", "dashboard", orgId],
      });
    },
  });
}
