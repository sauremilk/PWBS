import { apiClient } from "@/lib/api-client";
import type {
  ReminderListResponse,
  Reminder,
  UpdateReminderStatusRequest,
} from "@/types/api";

export async function listReminders(
  limit?: number,
): Promise<ReminderListResponse> {
  const qs = limit ? `?limit=${limit}` : "";
  return apiClient.get<ReminderListResponse>(`/reminders${qs}`);
}

export async function updateReminderStatus(
  id: string,
  body: UpdateReminderStatusRequest,
): Promise<Reminder> {
  return apiClient.patch<Reminder>(
    `/reminders/${encodeURIComponent(id)}`,
    body,
  );
}
