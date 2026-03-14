"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listReminders, updateReminderStatus } from "@/lib/api/reminders";
import type { ReminderStatus } from "@/types/api";

export function useReminders(limit?: number) {
  return useQuery({
    queryKey: ["reminders", limit],
    queryFn: () => listReminders(limit),
    refetchInterval: 60_000,
  });
}

export function useReminderCount() {
  return useQuery({
    queryKey: ["reminders", "count"],
    queryFn: () => listReminders(0),
    select: (data) => data.count,
    refetchInterval: 60_000,
  });
}

export function useUpdateReminderStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ReminderStatus }) =>
      updateReminderStatus(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminders"] });
    },
  });
}
