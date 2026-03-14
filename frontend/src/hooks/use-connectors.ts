"use client";

import { useQuery } from "@tanstack/react-query";
import { getConnectionStatus } from "@/lib/api/connectors";

export function useConnectionStatus() {
  return useQuery({
    queryKey: ["connectors", "status"],
    queryFn: getConnectionStatus,
    refetchInterval: 60_000,
  });
}
