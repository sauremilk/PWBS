"use client";

import { useQuery } from "@tanstack/react-query";
import { getSecurityStatus } from "@/lib/api/user";

export function useSecurityStatus() {
  return useQuery({
    queryKey: ["user", "security"],
    queryFn: getSecurityStatus,
  });
}
